"""
DSEX PRO - AI Analysis Generator (Step 2)
  =
Converts scored stock data into human-like professional insights.
Explains WHY a stock is bullish/bearish with structured reasoning.

Output:
  - headline      : One-line verdict (e.g. "Strong bullish — volume breakout + positive catalyst")
  - summary       : 2-3 sentence professional analysis
  - key_drivers   : Top 3 factors driving the signal (positive or negative)
  - risk_note     : Concise risk warning
  - action_note   : Actionable guidance for the investor
  - outlook_tag   : SHORT_TERM label (VERY_BULLISH / BULLISH / NEUTRAL / BEARISH / VERY_BEARISH)
"""

from dataclasses import dataclass, asdict, field
from typing import Optional
import json

# ── Import scoring structures from Step 1 ──────────────────────
# (In production, import from scoring_engine.py)
# For portability, key types are re-defined inline below.


#  
#  OUTPUT STRUCTURE
#  

@dataclass
class AIAnalysis:
    symbol: str
    name: str
    signal: str
    total_score: float
    confidence: float
    confidence_label: str
    risk_level: str

    # AI-generated text
    headline: str
    summary: str
    key_drivers: list          # list of {"factor": str, "direction": "+"/"-", "note": str}
    risk_note: str
    action_note: str
    outlook_tag: str           # VERY_BULLISH / BULLISH / NEUTRAL / BEARISH / VERY_BEARISH

    # Metadata
    price_change_pct: float
    volume_ratio: float


#  
#  LANGUAGE TEMPLATES
#  

# Factor descriptions (bullish & bearish versions)
FACTOR_LANG = {
    "trend_strength": {
        "+": [
            "strong price momentum with {pct:+.1f}% daily gain",
            "healthy uptrend supported by {pct:+.1f}% price move",
            "positive price action with stock near 52-week high",
        ],
        "-": [
            "price under pressure — down {pct:.1f}% with weak momentum",
            "deteriorating trend as stock slides toward 52-week low",
            "bearish price action with {pct:.1f}% decline today",
        ],
    },
    "volume_spike": {
        "+": [
            "volume surging at {vr:.1f}x the 20-day average — strong institutional interest",
            "exceptional volume ({vr:.1f}x average) confirming the bullish breakout",
            "high-conviction buying with {vr:.1f}x above-average volume",
        ],
        "-": [
            "elevated volume ({vr:.1f}x average) on a down-move signals distribution",
            "sell-side pressure amplified by {vr:.1f}x spike in trading volume",
            "unusual volume surge on decline suggests smart money exiting",
        ],
    },
    "news_sentiment": {
        "+": [
            "positive news flow boosting investor sentiment",
            "recent coverage is overwhelmingly favorable — market pricing in good news",
            "bullish catalyst from news/analyst coverage",
        ],
        "-": [
            "negative news sentiment weighing on price",
            "unfavorable media coverage creating headwinds",
            "bearish news cycle dampening investor confidence",
        ],
    },
    "event_impact": {
        "+": [
            "positive corporate event (dividend/expansion) acting as near-term catalyst",
            "upcoming corporate event expected to be a price catalyst",
            "event-driven tailwind supporting the bullish thesis",
        ],
        "-": [
            "negative corporate event increasing near-term uncertainty",
            "regulatory or corporate headwinds creating downside risk",
            "adverse event impact likely to cap upside potential",
        ],
    },
    "rsi_score": {
        "+": [
            "RSI at {rsi:.0f} — approaching oversold territory, bounce opportunity",
            "RSI ({rsi:.0f}) in healthy range with room to run higher",
            "momentum indicator (RSI {rsi:.0f}) not yet overbought — upside remains",
        ],
        "-": [
            "RSI at {rsi:.0f} — overbought territory signals near-term exhaustion",
            "RSI ({rsi:.0f}) flashing caution — reversal risk increasing",
            "momentum stretched (RSI {rsi:.0f}), pullback likely before next leg up",
        ],
    },
    "macd_score": {
        "+": [
            "MACD crossing above signal line — bullish crossover confirmed",
            "MACD histogram expanding positively — building upward momentum",
            "positive MACD divergence supporting continued upside",
        ],
        "-": [
            "MACD below signal line — bearish momentum dominates",
            "MACD crossover to downside confirms deteriorating trend",
            "negative MACD histogram — selling pressure accelerating",
        ],
    },
    "ema_alignment": {
        "+": [
            "textbook bull stack: price above EMA20 > EMA50 > EMA200",
            "all key moving averages aligned bullishly — strong trend structure",
            "price trading above all major EMAs — trend confirmation",
        ],
        "-": [
            "price trading below key moving averages — bearish alignment",
            "death cross structure forming — EMAs in bearish configuration",
            "stock below EMA20, 50, and 200 — no technical support",
        ],
    },
    "fundamental_score": {
        "+": [
            "trading at a discount to sector PE — undervalued opportunity",
            "strong EPS growth of {eps:.0f}% YoY with attractive valuation",
            "fundamentals support the thesis: below-sector PE with growing earnings",
        ],
        "-": [
            "premium valuation vs. sector peers limits upside potential",
            "earnings deterioration ({eps:.0f}% YoY) undermining the bull case",
            "overvalued vs. sector — PE expansion unlikely from here",
        ],
    },
}

# Signal headlines
HEADLINE_TEMPLATES = {
    "STRONG_BUY": [
        "🟢 Strong bullish conviction — multiple factors aligned for upside",
        "🟢 High-confidence BUY — breakout confirmed with fundamental support",
        "🟢 Exceptional setup: trend, volume, and momentum all point higher",
    ],
    "BUY": [
        "🔵 Bullish bias — key indicators favor continued upside",
        "🔵 Positive outlook — technical and sentiment factors aligned",
        "🔵 Buy signal with moderate conviction — risk-reward favorable",
    ],
    "NEUTRAL": [
        "⚪ Mixed signals — no clear directional edge at this time",
        "⚪ Wait-and-watch: bulls and bears evenly matched",
        "⚪ Consolidation phase — no strong trigger in either direction",
    ],
    "SELL": [
        "🟠 Bearish lean — technical deterioration outweighs positives",
        "🟠 Sell signal with moderate conviction — protect capital",
        "🟠 Downside risk elevated — consider reducing exposure",
    ],
    "STRONG_SELL": [
        "🔴 Strong bearish conviction — multiple red flags across factors",
        "🔴 High-confidence SELL — trend, volume, and sentiment all negative",
        "🔴 Avoid or exit — technical and fundamental picture is deteriorating",
    ],
}

# Action notes by signal + risk
ACTION_TEMPLATES = {
    ("STRONG_BUY",  "LOW"):       "Strong entry opportunity. Consider building a full position with a stop below the 20-day EMA.",
    ("STRONG_BUY",  "MEDIUM"):    "Good entry point. Start with 60-70% of target position; add on confirmed breakout.",
    ("STRONG_BUY",  "HIGH"):      "Bullish but volatile. Use a scaled entry and maintain a strict stop-loss below recent support.",
    ("STRONG_BUY",  "VERY_HIGH"): "High reward but speculative. Small position only — volatility risk is significant.",
    ("BUY",         "LOW"):       "Favorable entry. Build position gradually; set a trailing stop to protect gains.",
    ("BUY",         "MEDIUM"):    "Positive risk-reward. Enter on minor pullbacks to the 20 EMA for better price.",
    ("BUY",         "HIGH"):      "Bullish signal but elevated risk. Smaller position size and clear stop-loss recommended.",
    ("BUY",         "VERY_HIGH"): "Wait for confirmation candle before entering — high volatility increases whipsaw risk.",
    ("NEUTRAL",     "LOW"):       "Hold existing positions. Avoid adding until a clear directional breakout emerges.",
    ("NEUTRAL",     "MEDIUM"):    "Sideline for now. Monitor for a volume-confirmed move above resistance or below support.",
    ("NEUTRAL",     "HIGH"):      "High risk with no clear signal — best to stay out until volatility settles.",
    ("NEUTRAL",     "VERY_HIGH"): "Avoid. Risk-adjusted return is unfavorable in both directions.",
    ("SELL",        "LOW"):       "Reduce exposure. Consider trimming 50% of position and tightening remaining stop.",
    ("SELL",        "MEDIUM"):    "Exit or hedge. The technical picture favors further downside in the near term.",
    ("SELL",        "HIGH"):      "Exit position. Risk of a sharper decline is elevated given high volatility.",
    ("SELL",        "VERY_HIGH"): "Exit immediately. High-risk bearish setup with potential for significant capital loss.",
    ("STRONG_SELL", "LOW"):       "Exit all positions. Even with low volatility, the downside thesis is compelling.",
    ("STRONG_SELL", "MEDIUM"):    "Full exit recommended. Breadth of bearish signals leaves little margin of safety.",
    ("STRONG_SELL", "HIGH"):      "Urgent exit. Multiple red flags combined with high volatility — capital preservation priority.",
    ("STRONG_SELL", "VERY_HIGH"): "Exit immediately. This is a high-conviction bearish setup with very high volatility — maximum risk.",
}

# Risk notes by level
RISK_NOTES = {
    "LOW":       "Low volatility profile. Standard position sizing appropriate. Stop-loss below 20-EMA recommended.",
    "MEDIUM":    "Moderate volatility. Use 75% of normal position size. ATR-based stop recommended.",
    "HIGH":      "Elevated ATR and/or RSI extremes detected. Reduce position size by 40-50%. Risk of sharp reversal.",
    "VERY_HIGH": "⚠️ Very high volatility. Extreme RSI, abnormal volume, or adverse news. Minimal exposure only — treat as speculative.",
}

# Outlook tags
OUTLOOK_MAP = {
    "STRONG_BUY":  "VERY_BULLISH",
    "BUY":         "BULLISH",
    "NEUTRAL":     "NEUTRAL",
    "SELL":        "BEARISH",
    "STRONG_SELL": "VERY_BEARISH",
}


#  
#  DRIVER EXTRACTOR
#  

def _get_top_drivers(breakdown: dict, stock_data: dict, n: int = 3) -> list:
    """
    Pick the top N most impactful factors (highest deviation from neutral 5).
    Returns structured driver objects with direction and explanation.
    """
    # Score each factor by how extreme it is (distance from 5)
    factor_impact = []
    for key, score in breakdown.items():
        impact = abs(score - 5)
        direction = "+" if score >= 5 else "-"
        factor_impact.append((key, score, direction, impact))

    # Sort by impact (most extreme first)
    factor_impact.sort(key=lambda x: x[3], reverse=True)
    top = factor_impact[:n]

    drivers = []
    for key, score, direction, _ in top:
        templates = FACTOR_LANG.get(key, {}).get(direction, ["Significant factor in this analysis"])
        # Pick template deterministically by score bucket
        idx = min(int(score / 3.5), len(templates) - 1) if direction == "+" else min(int((10 - score) / 3.5), len(templates) - 1)
        template = templates[idx]

        # Fill placeholders
        note = template.format(
            pct=stock_data.get("price_change_pct", 0),
            vr=stock_data.get("volume_ratio", 1),
            rsi=stock_data.get("rsi", 50),
            eps=stock_data.get("eps_growth_yoy", 0) or 0,
        )

        drivers.append({
            "factor": key,
            "score": round(score, 2),
            "direction": direction,
            "note": note,
        })

    return drivers


#  
#  SUMMARY BUILDER
#  

def _build_summary(signal: str, score: float, confidence: float,
                   drivers: list, stock_data: dict) -> str:
    """Build a 2-3 sentence professional analysis summary."""
    name      = stock_data.get("name", "This stock")
    pct       = stock_data.get("price_change_pct", 0)
    vr        = stock_data.get("volume_ratio", 1)
    conf_word = {"HIGH": "high", "MEDIUM": "moderate", "LOW": "low"}[
                    stock_data.get("confidence_label", "MEDIUM")]

    # Opening sentence — overall verdict
    if signal == "STRONG_BUY":
        s1 = f"{name} presents a high-conviction bullish setup (score {score}/10) with {conf_word} confidence across multiple aligned indicators."
    elif signal == "BUY":
        s1 = f"{name} shows a favorable bullish setup (score {score}/10) with {conf_word} signal confidence."
    elif signal == "NEUTRAL":
        s1 = f"{name} is in a consolidation phase (score {score}/10) with no dominant directional edge currently."
    elif signal == "SELL":
        s1 = f"{name} is exhibiting bearish characteristics (score {score}/10) with {conf_word} confidence in the downside signal."
    else:
        s1 = f"{name} shows strong bearish pressure (score {score}/10) with {conf_word} confidence in continued weakness."

    # Middle sentence — key driver narrative
    pos_drivers = [d for d in drivers if d["direction"] == "+"]
    neg_drivers = [d for d in drivers if d["direction"] == "-"]

    if pos_drivers and neg_drivers:
        s2 = f"Key positives include {pos_drivers[0]['note'].lower()}, while concerns around {neg_drivers[0]['note'].lower()} create some headwind."
    elif pos_drivers:
        s2 = f"Primary drivers include {pos_drivers[0]['note'].lower()}" + \
             (f" and {pos_drivers[1]['note'].lower()}" if len(pos_drivers) > 1 else "") + "."
    elif neg_drivers:
        s2 = f"Primary concerns include {neg_drivers[0]['note'].lower()}" + \
             (f" and {neg_drivers[1]['note'].lower()}" if len(neg_drivers) > 1 else "") + "."
    else:
        s2 = "Indicators are mixed with no dominant factor."

    # Closing — volume/price context
    if vr >= 2.0:
        s3 = f"The {vr:.1f}x volume surge adds credibility to the signal and suggests institutional activity."
    elif pct > 2:
        s3 = f"A {pct:+.1f}% session gain with sustained buying interest supports the bullish case."
    elif pct < -2:
        s3 = f"A {pct:.1f}% session decline with no clear catalyst suggests continued selling pressure."
    else:
        s3 = f"Volume and price action are in line with historical norms — no extreme readings."

    return f"{s1} {s2} {s3}"


#  
#  MAIN GENERATOR
#  

def generate_analysis(scored_stock: dict) -> AIAnalysis:
    """
    Takes the output of score_stock() (as dict) and returns AIAnalysis.
    """
    symbol    = scored_stock["symbol"]
    name      = scored_stock["name"]
    signal    = scored_stock["signal"]
    score     = scored_stock["total_score"]
    conf      = scored_stock["confidence"]
    conf_lbl  = scored_stock["confidence_label"]
    risk      = scored_stock["risk_level"]
    breakdown = scored_stock["breakdown"]
    pct       = scored_stock["price_change_pct"]
    vr        = scored_stock["volume_ratio"]

    # Enrich with raw fields for template filling
    stock_data = {
        "name": name,
        "price_change_pct": pct,
        "volume_ratio": vr,
        "rsi": scored_stock.get("rsi_raw", 50),
        "eps_growth_yoy": scored_stock.get("eps_growth_yoy", 0),
        "confidence_label": conf_lbl,
    }

    # 1. Key drivers
    drivers = _get_top_drivers(breakdown, stock_data, n=3)

    # 2. Summary
    summary = _build_summary(signal, score, conf, drivers, stock_data)

    # 3. Headline (pick by score bucket within signal)
    headlines = HEADLINE_TEMPLATES[signal]
    idx = min(int((score % 2) * len(headlines) / 2), len(headlines) - 1)
    base_headline = headlines[idx]

    # Append top driver to headline for specificity
    if drivers:
        top = drivers[0]["note"].split("—")[0].split(" — ")[0].strip().rstrip(".")
        headline = f"{base_headline.split('—')[0].strip()} — {top}"
    else:
        headline = base_headline

    # 4. Risk note
    risk_note = RISK_NOTES[risk]

    # 5. Action note
    action_note = ACTION_TEMPLATES.get(
        (signal, risk),
        "Assess risk-reward carefully before taking a position."
    )

    # 6. Outlook tag
    outlook_tag = OUTLOOK_MAP[signal]

    return AIAnalysis(
        symbol=symbol, name=name, signal=signal, total_score=score,
        confidence=conf, confidence_label=conf_lbl, risk_level=risk,
        headline=headline, summary=summary, key_drivers=drivers,
        risk_note=risk_note, action_note=action_note, outlook_tag=outlook_tag,
        price_change_pct=pct, volume_ratio=vr,
    )


def generate_batch(scored_stocks: list) -> list:
    """Generate AI analysis for a list of scored stocks."""
    return [generate_analysis(s) for s in scored_stocks]


def export_analysis_json(analyses: list) -> str:
    """Serialize to JSON."""
    return json.dumps([asdict(a) for a in analyses], indent=2, ensure_ascii=False)


#  
#  DEMO
#  

if __name__ == "__main__":
    # Simulate Step 1 output
    mock_scored = [
        {
            "symbol": "SQURPHARMA", "name": "Square Pharmaceuticals",
            "signal": "BUY", "total_score": 7.32, "confidence": 78.6,
            "confidence_label": "HIGH", "risk_level": "MEDIUM",
            "breakdown": {
                "trend_strength": 7.25, "volume_spike": 7.08,
                "news_sentiment": 8.0,  "event_impact": 6.5,
                "rsi_score": 6.0,       "macd_score": 6.75,
                "ema_alignment": 10.0,  "volatility_score": 7.31,
                "fundamental_score": 9.59, "market_context": 6.0,
            },
            "price_change_pct": 3.29, "volume_ratio": 2.12,
            "rsi_raw": 58, "eps_growth_yoy": 15,
        },
        {
            "symbol": "BEXIMCO", "name": "Beximco Limited",
            "signal": "SELL", "total_score": 3.33, "confidence": 49.4,
            "confidence_label": "LOW", "risk_level": "MEDIUM",
            "breakdown": {
                "trend_strength": 0.8,  "volume_spike": 4.4,
                "news_sentiment": 3.0,  "event_impact": 4.0,
                "rsi_score": 7.5,       "macd_score": 3.5,
                "ema_alignment": 0.0,   "volatility_score": 4.7,
                "fundamental_score": 4.8, "market_context": 5.5,
            },
            "price_change_pct": -6.95, "volume_ratio": 1.33,
            "rsi_raw": 38, "eps_growth_yoy": -8,
        },
        {
            "symbol": "GRAMEENPHONE", "name": "Grameenphone Ltd",
            "signal": "NEUTRAL", "total_score": 6.32, "confidence": 46.6,
            "confidence_label": "LOW", "risk_level": "MEDIUM",
            "breakdown": {
                "trend_strength": 6.3,  "volume_spike": 3.8,
                "news_sentiment": 6.5,  "event_impact": 7.5,
                "rsi_score": 5.5,       "macd_score": 6.2,
                "ema_alignment": 10.0,  "volatility_score": 6.7,
                "fundamental_score": 9.9, "market_context": 6.0,
            },
            "price_change_pct": 1.64, "volume_ratio": 1.14,
            "rsi_raw": 62, "eps_growth_yoy": 10,
        },
    ]

    analyses = generate_batch(mock_scored)

    print("=" * 70)
    print("  DSEX PRO — AI ANALYSIS GENERATOR  (Step 2)")
    print("=" * 70)

    for a in analyses:
        print(f"\n{'─'*70}")
        print(f"  [{a.signal}] {a.symbol} — {a.name}")
        print(f"  Score: {a.total_score}/10  |  Confidence: {a.confidence}% ({a.confidence_label})  |  Risk: {a.risk_level}")
        print(f"\n  HEADLINE:")
        print(f"    {a.headline}")
        print(f"\n  OUTLOOK: {a.outlook_tag}")
        print(f"\n  SUMMARY:")
        for line in a.summary.split(". "):
            if line.strip():
                print(f"    • {line.strip().rstrip('.')}.")
        print(f"\n  KEY DRIVERS:")
        for d in a.key_drivers:
            icon = "▲" if d["direction"] == "+" else "▼"
            print(f"    {icon} [{d['factor']}] {d['note']}  (score: {d['score']}/10)")
        print(f"\n  RISK NOTE:")
        print(f"    {a.risk_note}")
        print(f"\n  ACTION:")
        print(f"    → {a.action_note}")

    print(f"\n{'='*70}")
    print("  JSON Output (first stock):")
    print(export_analysis_json(analyses[:1]))
