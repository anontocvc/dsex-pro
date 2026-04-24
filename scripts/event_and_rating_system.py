"""
DSEX PRO - Event Detection System (Step 3) + Stock Rating System (Step 4)

STEP 3: Detects and classifies:
  - Dividend announcements
  - IPO / Rights Share news
  - AGM / EGM events
  - Regulatory / BSEC actions
  - Earnings releases
  - Bonus share declarations
  - Circuit breaker triggers

STEP 4: Produces a unified stock rating:
  - Rating      : 1–10 (investment grade)
  - Risk Level  : LOW / MEDIUM / HIGH / VERY_HIGH
  - Confidence  : 0–100%
  - Grade Label : A+ / A / B+ / B / C / D / F
  - Investment  : STRONG BUY → STRONG SELL
"""

import json
from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import date, timedelta
import math


#  
#  STEP 3: EVENT DETECTION
#  

# Event type constants
class EventType:
    DIVIDEND          = "DIVIDEND"
    BONUS_SHARE       = "BONUS_SHARE"
    RIGHTS_SHARE      = "RIGHTS_SHARE"
    IPO               = "IPO"
    AGM               = "AGM"
    EGM               = "EGM"
    EARNINGS_RELEASE  = "EARNINGS_RELEASE"
    REGULATORY_ACTION = "REGULATORY_ACTION"
    CIRCUIT_BREAKER   = "CIRCUIT_BREAKER"
    INSIDER_TRADE     = "INSIDER_TRADE"
    MERGER_ACQUISITION= "MERGER_ACQUISITION"
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"
    SUSPENSION        = "SUSPENSION"


@dataclass
class CorporateEvent:
    """A detected corporate or market event."""
    event_type: str             # EventType constant
    symbol: str
    title: str                  # Human-readable title
    description: str            # Detail
    impact_score: float         # -1.0 (very negative) to +1.0 (very positive)
    impact_label: str           # VERY_POSITIVE / POSITIVE / NEUTRAL / NEGATIVE / VERY_NEGATIVE
    urgency: str                # HIGH / MEDIUM / LOW
    event_date: str             # ISO date string
    days_until: int             # negative = past, 0 = today, positive = future
    source: str                 # "DSE_ANNOUNCEMENT" / "BSEC" / "NEWS" / "MANUAL"
    raw_data: dict = field(default_factory=dict)


@dataclass
class EventSummary:
    """Aggregated event picture for a stock."""
    symbol: str
    total_events: int
    composite_impact: float      # -1 to +1 weighted average
    impact_label: str
    has_urgent_event: bool
    dominant_event_type: str
    events: list                 # list of CorporateEvent (as dicts)
    alert_message: str           # Top-level message for notification


# ── EVENT CLASSIFIER ──────────────────────────

EVENT_IMPACT_MAP = {
    EventType.DIVIDEND:           +0.55,
    EventType.BONUS_SHARE:        +0.60,
    EventType.RIGHTS_SHARE:       +0.20,   # dilutive but shows confidence
    EventType.IPO:                +0.70,
    EventType.AGM:                +0.10,
    EventType.EGM:                -0.10,   # often called for bad news
    EventType.EARNINGS_RELEASE:    0.00,   # depends on result (override per event)
    EventType.REGULATORY_ACTION:  -0.65,
    EventType.CIRCUIT_BREAKER:    -0.80,
    EventType.INSIDER_TRADE:      +0.30,   # buying; use -0.40 if selling
    EventType.MERGER_ACQUISITION: +0.50,
    EventType.MANAGEMENT_CHANGE:  -0.15,
    EventType.SUSPENSION:         -0.90,
}

URGENCY_RULES = {
    EventType.CIRCUIT_BREAKER:    "HIGH",
    EventType.SUSPENSION:         "HIGH",
    EventType.REGULATORY_ACTION:  "HIGH",
    EventType.DIVIDEND:           "MEDIUM",
    EventType.BONUS_SHARE:        "MEDIUM",
    EventType.EARNINGS_RELEASE:   "MEDIUM",
    EventType.IPO:                "MEDIUM",
    EventType.AGM:                "LOW",
    EventType.EGM:                "MEDIUM",
    EventType.RIGHTS_SHARE:       "LOW",
    EventType.INSIDER_TRADE:      "LOW",
    EventType.MERGER_ACQUISITION: "HIGH",
    EventType.MANAGEMENT_CHANGE:  "LOW",
}


def _impact_label(score: float) -> str:
    if score >= 0.5:   return "VERY_POSITIVE"
    if score >= 0.2:   return "POSITIVE"
    if score >= -0.2:  return "NEUTRAL"
    if score >= -0.5:  return "NEGATIVE"
    return "VERY_NEGATIVE"


def create_event(
    event_type: str,
    symbol: str,
    title: str,
    description: str,
    event_date: str,
    source: str = "DSE_ANNOUNCEMENT",
    impact_override: Optional[float] = None,
    raw_data: dict = None,
) -> CorporateEvent:
    """Factory: create a CorporateEvent from minimal inputs."""
    impact = impact_override if impact_override is not None else EVENT_IMPACT_MAP.get(event_type, 0.0)
    days_until = (date.fromisoformat(event_date) - date.today()).days

    return CorporateEvent(
        event_type    = event_type,
        symbol        = symbol,
        title         = title,
        description   = description,
        impact_score  = round(impact, 2),
        impact_label  = _impact_label(impact),
        urgency       = URGENCY_RULES.get(event_type, "LOW"),
        event_date    = event_date,
        days_until    = days_until,
        source        = source,
        raw_data      = raw_data or {},
    )


def build_event_summary(symbol: str, events: list) -> EventSummary:
    """Aggregate multiple events into a single EventSummary."""
    if not events:
        return EventSummary(
            symbol=symbol, total_events=0,
            composite_impact=0.0, impact_label="NEUTRAL",
            has_urgent_event=False, dominant_event_type="NONE",
            events=[], alert_message="No significant events detected."
        )

    # Weight recent/urgent events more
    def event_weight(e: CorporateEvent) -> float:
        recency = max(0, 1 - abs(e.days_until) / 30)  # 0 to 1 based on proximity
        urgency_w = {"HIGH": 1.5, "MEDIUM": 1.0, "LOW": 0.6}[e.urgency]
        return recency * urgency_w

    total_w = sum(event_weight(e) for e in events) or 1
    composite = sum(e.impact_score * event_weight(e) for e in events) / total_w
    composite = round(max(-1.0, min(1.0, composite)), 3)

    has_urgent = any(e.urgency == "HIGH" for e in events)

    # Dominant event type (highest impact magnitude)
    dominant = max(events, key=lambda e: abs(e.impact_score))

    # Build alert message
    if abs(composite) >= 0.5:
        top = events[0]
        prefix = "🚨 HIGH IMPACT" if has_urgent else "📢 ALERT"
        alert = f"{prefix}: {top.title} — {top.description}"
    elif abs(composite) >= 0.2:
        top = events[0]
        alert = f"📋 EVENT: {top.title} — monitor for price reaction"
    else:
        alert = f"ℹ️ {len(events)} event(s) detected — low impact on near-term price."

    return EventSummary(
        symbol           = symbol,
        total_events     = len(events),
        composite_impact = composite,
        impact_label     = _impact_label(composite),
        has_urgent_event = has_urgent,
        dominant_event_type = dominant.event_type,
        events           = [asdict(e) for e in events],
        alert_message    = alert,
    )


#  
#  STEP 4: STOCK RATING SYSTEM
#  

GRADE_MAP = [
    (9.0, "A+", "EXCEPTIONAL"),
    (8.0, "A",  "EXCELLENT"),
    (7.0, "B+", "GOOD"),
    (6.0, "B",  "ABOVE_AVERAGE"),
    (5.0, "C+", "AVERAGE"),
    (4.0, "C",  "BELOW_AVERAGE"),
    (3.0, "D",  "POOR"),
    (0.0, "F",  "VERY_POOR"),
]

INVESTMENT_MAP = [
    (8.5, "STRONG BUY"),
    (7.0, "BUY"),
    (5.5, "ACCUMULATE"),
    (4.5, "HOLD"),
    (3.5, "REDUCE"),
    (2.0, "SELL"),
    (0.0, "STRONG SELL"),
]


@dataclass
class StockRating:
    """Final unified rating for a stock — Step 4 output."""
    symbol: str
    name: str

    # Core rating
    rating: float           # 1.0 – 10.0
    grade: str              # A+ / A / B+ / B / C+ / C / D / F
    grade_label: str        # EXCEPTIONAL → VERY_POOR
    investment: str         # STRONG BUY → STRONG SELL

    # Risk + Confidence (from Step 1)
    risk_level: str         # LOW / MEDIUM / HIGH / VERY_HIGH
    confidence: float       # 0 – 100 %
    confidence_label: str   # HIGH / MEDIUM / LOW

    # Component scores (0–10)
    technical_score: float   # from Step 1 breakdown
    fundamental_score: float # PE, EPS
    event_score: float       # from Step 3 event impact
    sentiment_score: float   # news + volume

    # Event summary (Step 3)
    event_summary: dict      # EventSummary as dict

    # Reasoning (Step 2 style)
    rating_rationale: str
    key_positives: list
    key_negatives: list
    target_horizon: str      # "1–3 DAYS" / "1–2 WEEKS" / "1 MONTH"
    stop_loss_note: str


def _derive_technical_score(breakdown: dict) -> float:
    """Average the technical factors from Step 1 breakdown."""
    tech_keys = ["trend_strength", "volume_spike", "rsi_score",
                 "macd_score", "ema_alignment", "volatility_score"]
    vals = [breakdown.get(k, 5) for k in tech_keys]
    return round(sum(vals) / len(vals), 2)


def _derive_sentiment_score(breakdown: dict) -> float:
    sentiment_keys = ["news_sentiment", "event_impact", "market_context"]
    vals = [breakdown.get(k, 5) for k in sentiment_keys]
    return round(sum(vals) / len(vals), 2)


def _event_impact_to_score(impact: float) -> float:
    """Convert -1..+1 event composite to 0..10 score."""
    return round((impact + 1) / 2 * 10, 2)


def _get_grade(rating: float) -> tuple:
    for threshold, grade, label in GRADE_MAP:
        if rating >= threshold:
            return grade, label
    return "F", "VERY_POOR"


def _get_investment(rating: float) -> str:
    for threshold, label in INVESTMENT_MAP:
        if rating >= threshold:
            return label
    return "STRONG SELL"


def _build_rationale(rating: float, grade: str, tech: float, fund: float,
                     event: float, sent: float, risk: str) -> str:
    parts = []
    if tech >= 7:
        parts.append(f"strong technical setup ({tech:.1f}/10)")
    elif tech <= 4:
        parts.append(f"weak technical structure ({tech:.1f}/10)")
    else:
        parts.append(f"mixed technical picture ({tech:.1f}/10)")

    if fund >= 7:
        parts.append(f"attractive fundamentals ({fund:.1f}/10)")
    elif fund <= 4:
        parts.append(f"concerning fundamentals ({fund:.1f}/10)")

    if event >= 7:
        parts.append("positive corporate events acting as catalyst")
    elif event <= 3:
        parts.append("negative event overhang creating headwind")

    risk_text = {
        "LOW": "low-risk profile supports position sizing",
        "MEDIUM": "moderate risk — standard caution advised",
        "HIGH": "high volatility — reduce exposure",
        "VERY_HIGH": "very high risk — speculative only",
    }[risk]

    return f"Grade {grade} stock with rating {rating:.1f}/10. " + \
           ", ".join(parts).capitalize() + f". {risk_text}."


def _extract_positives_negatives(breakdown: dict, event_score: float) -> tuple:
    all_factors = {
        "Trend Strength": breakdown.get("trend_strength", 5),
        "Volume Spike": breakdown.get("volume_spike", 5),
        "EMA Alignment": breakdown.get("ema_alignment", 5),
        "MACD": breakdown.get("macd_score", 5),
        "RSI Signal": breakdown.get("rsi_score", 5),
        "Fundamentals": breakdown.get("fundamental_score", 5),
        "News Sentiment": breakdown.get("news_sentiment", 5),
        "Event Impact": event_score,
    }
    positives = [(k, v) for k, v in all_factors.items() if v >= 6.5]
    negatives = [(k, v) for k, v in all_factors.items() if v <= 3.5]
    positives.sort(key=lambda x: x[1], reverse=True)
    negatives.sort(key=lambda x: x[1])

    pos_list = [f"{k} ({v:.1f}/10)" for k, v in positives[:3]]
    neg_list = [f"{k} ({v:.1f}/10)" for k, v in negatives[:3]]
    return pos_list, neg_list


def _target_horizon(signal: str, risk: str) -> str:
    if signal in ("STRONG BUY", "STRONG SELL"):
        return "1–3 DAYS"
    if risk in ("HIGH", "VERY_HIGH"):
        return "1–3 DAYS"
    if signal in ("BUY", "SELL"):
        return "1–2 WEEKS"
    return "1 MONTH"


def _stop_loss_note(risk: str, atr_pct: float) -> str:
    if risk == "LOW":
        return f"Place stop-loss 1.5× ATR ({atr_pct:.1f}%) below entry — tight stop justified."
    if risk == "MEDIUM":
        return f"Place stop-loss 2× ATR ({atr_pct:.1f}%) below entry — standard stop."
    if risk == "HIGH":
        return f"Place stop-loss 2.5× ATR ({atr_pct:.1f}%) below entry — wider stop needed."
    return f"Place stop-loss 3× ATR ({atr_pct:.1f}%) below entry or avoid — very high risk."


def build_stock_rating(
    scored_stock: dict,
    event_summary: EventSummary,
    atr_pct: float = 2.0,
) -> StockRating:
    """
    Combine Step 1 score + Step 3 events → unified Step 4 rating.
    """
    breakdown = scored_stock["breakdown"]
    signal    = scored_stock["signal"]
    risk      = scored_stock["risk_level"]

    # Component scores
    tech  = _derive_technical_score(breakdown)
    fund  = breakdown.get("fundamental_score", 5)
    event = _event_impact_to_score(event_summary.composite_impact)
    sent  = _derive_sentiment_score(breakdown)

    # Composite rating (weighted blend)
    rating = (
        tech  * 0.40 +
        fund  * 0.20 +
        event * 0.25 +
        sent  * 0.15
    )
    rating = round(max(1, min(10, rating)), 2)

    grade, grade_label   = _get_grade(rating)
    investment           = _get_investment(rating)
    rationale            = _build_rationale(rating, grade, tech, fund, event, sent, risk)
    positives, negatives = _extract_positives_negatives(breakdown, event)
    horizon              = _target_horizon(investment, risk)
    stop_note            = _stop_loss_note(risk, atr_pct)

    return StockRating(
        symbol           = scored_stock["symbol"],
        name             = scored_stock["name"],
        rating           = rating,
        grade            = grade,
        grade_label      = grade_label,
        investment       = investment,
        risk_level       = risk,
        confidence       = scored_stock["confidence"],
        confidence_label = scored_stock["confidence_label"],
        technical_score  = tech,
        fundamental_score= fund,
        event_score      = event,
        sentiment_score  = sent,
        event_summary    = asdict(event_summary),
        rating_rationale = rationale,
        key_positives    = positives,
        key_negatives    = negatives,
        target_horizon   = horizon,
        stop_loss_note   = stop_note,
    )


#  
#  DEMO
#  

if __name__ == "__main__":
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    next_week = (date.today() + timedelta(days=7)).isoformat()

    # ── Sample events  
    squrpharma_events = [
        create_event(EventType.DIVIDEND, "SQURPHARMA",
                     "Cash Dividend Declared — 35%",
                     "Board declared BDT 3.50 per share cash dividend for FY2024",
                     next_week, impact_override=0.65),
        create_event(EventType.EARNINGS_RELEASE, "SQURPHARMA",
                     "Q2 FY2024 Earnings — EPS up 18%",
                     "Net profit rose 18% YoY to BDT 842 crore, beating estimates",
                     today, impact_override=0.50),
    ]
    beximco_events = [
        create_event(EventType.REGULATORY_ACTION, "BEXIMCO",
                     "BSEC Probe Initiated",
                     "BSEC opens investigation into related-party transactions",
                     today, impact_override=-0.70),
        create_event(EventType.CIRCUIT_BREAKER, "BEXIMCO",
                     "Circuit Breaker Triggered — Lower",
                     "Stock hit 10% lower circuit breaker during morning session",
                     today, impact_override=-0.85),
    ]
    gp_events = [
        create_event(EventType.AGM, "GRAMEENPHONE",
                     "Annual General Meeting — April 30",
                     "AGM scheduled. Board to discuss dividend approval and expansion plans.",
                     next_week, impact_override=0.15),
    ]

    # Build event summaries
    squr_summary = build_event_summary("SQURPHARMA", squrpharma_events)
    bexi_summary = build_event_summary("BEXIMCO",    beximco_events)
    gp_summary   = build_event_summary("GRAMEENPHONE", gp_events)

    # ── Simulate Step 1 scored stocks ──────────────────────────────
    scored = [
        {
            "symbol": "SQURPHARMA", "name": "Square Pharmaceuticals",
            "signal": "BUY", "total_score": 7.32, "confidence": 78.6,
            "confidence_label": "HIGH", "risk_level": "MEDIUM",
            "breakdown": {"trend_strength":7.25,"volume_spike":7.08,"news_sentiment":8.0,
                          "event_impact":6.5,"rsi_score":6.0,"macd_score":6.75,
                          "ema_alignment":10.0,"volatility_score":7.31,"fundamental_score":9.59,"market_context":6.0},
            "price_change_pct": 3.29, "volume_ratio": 2.12,
        },
        {
            "symbol": "BEXIMCO", "name": "Beximco Limited",
            "signal": "SELL", "total_score": 3.33, "confidence": 49.4,
            "confidence_label": "LOW", "risk_level": "HIGH",
            "breakdown": {"trend_strength":0.8,"volume_spike":4.4,"news_sentiment":3.0,
                          "event_impact":4.0,"rsi_score":7.5,"macd_score":3.5,
                          "ema_alignment":0.0,"volatility_score":4.7,"fundamental_score":4.8,"market_context":5.5},
            "price_change_pct": -6.95, "volume_ratio": 1.33,
        },
        {
            "symbol": "GRAMEENPHONE", "name": "Grameenphone Ltd",
            "signal": "NEUTRAL", "total_score": 6.32, "confidence": 46.6,
            "confidence_label": "LOW", "risk_level": "MEDIUM",
            "breakdown": {"trend_strength":6.3,"volume_spike":3.8,"news_sentiment":6.5,
                          "event_impact":7.5,"rsi_score":5.5,"macd_score":6.2,
                          "ema_alignment":10.0,"volatility_score":6.7,"fundamental_score":9.9,"market_context":6.0},
            "price_change_pct": 1.64, "volume_ratio": 1.14,
        },
    ]
    event_summaries = [squr_summary, bexi_summary, gp_summary]

    ratings = [build_stock_rating(s, e, atr_pct=2.2)
               for s, e in zip(scored, event_summaries)]

    # ── Print output  ─
    print("=" * 70)
    print("  DSEX PRO — STEP 3: EVENT DETECTION + STEP 4: RATING SYSTEM")
    print("=" * 70)

    for r, ev in zip(ratings, event_summaries):
        print(f"\n{'─'*70}")
        print(f"  {r.symbol} — {r.name}")
        print(f"\n  ── STEP 3: EVENTS ──")
        print(f"  Events detected : {ev.total_events}")
        print(f"  Composite impact: {ev.composite_impact:+.3f}  ({ev.impact_label})")
        print(f"  Urgent event    : {'YES ⚠️' if ev.has_urgent_event else 'No'}")
        print(f"  Alert           : {ev.alert_message}")
        for e in ev.events:
            icon = "▲" if e['impact_score'] > 0 else "▼"
            print(f"    {icon} [{e['event_type']}] {e['title']} | Impact: {e['impact_score']:+.2f} | {e['urgency']} urgency")

        print(f"\n  ── STEP 4: RATING ──")
        print(f"  Rating     : {r.rating}/10  |  Grade: {r.grade} ({r.grade_label})")
        print(f"  Investment : {r.investment}")
        print(f"  Risk Level : {r.risk_level}")
        print(f"  Confidence : {r.confidence}% ({r.confidence_label})")
        print(f"  Horizon    : {r.target_horizon}")
        print(f"\n  Component Scores:")
        bars = [
            ("Technical",    r.technical_score),
            ("Fundamental",  r.fundamental_score),
            ("Event Impact", r.event_score),
            ("Sentiment",    r.sentiment_score),
        ]
        for label, score in bars:
            bar = "█" * int(score) + "░" * (10 - int(score))
            print(f"    {label:14s} {bar} {score:.1f}/10")
        print(f"\n  ✅ Positives: {', '.join(r.key_positives) or 'None'}")
        print(f"  ❌ Negatives: {', '.join(r.key_negatives) or 'None'}")
        print(f"\n  Rationale  : {r.rating_rationale}")
        print(f"  Stop Loss  : {r.stop_loss_note}")

    print(f"\n{'='*70}")
    print("  JSON (first stock):")
    print(json.dumps(asdict(ratings[0]), indent=2, ensure_ascii=False)[:1200] + "\n  ...")
