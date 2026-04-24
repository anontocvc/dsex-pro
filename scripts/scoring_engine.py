<<<<<<< HEAD
def score_stock(df):
    score = 0

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # =========================
    # TREND (STRONG TREND)
    # =========================
    if last["ema20"] > last["ema50"]:
        score += 2

        # stronger trend
        if last["close"] > last["ema20"]:
            score += 1
    else:
        score -= 2

    # =========================
    # RSI MOMENTUM
    # =========================
    if 55 < last["rsi"] < 70:
        score += 2
    elif last["rsi"] > 70:
        score -= 1
    elif last["rsi"] < 40:
        score -= 2

    # =========================
    # MOMENTUM ACCELERATION
    # =========================
    if last["close"] > prev["close"]:
        score += 1

    # =========================
    # BREAKOUT (NEW HIGH)
    # =========================
    if last["close"] >= df["close"].rolling(20).max().iloc[-1]:
        score += 2

    # =========================
    # VOLUME EXPLOSION
    # =========================
    if last["volume"] > (1.5 * last["vol_ma20"]):
        score += 2
    elif last["volume"] > last["vol_ma20"]:
        score += 1

    # =========================
    # WEAK STOCK PENALTY
    # =========================
    if last["close"] < last["ema50"]:
        score -= 2

    return score
=======
"""
DSEX PRO - Advanced Scoring Engine (Step 1)
============================================
Weighted multi-factor scoring model for Bangladesh stock market.
Produces: Score (0-10), Signal Strength, Confidence Level
"""

import json
import math
from dataclasses import dataclass, asdict
from typing import Optional


# ─────────────────────────────────────────────
#  DATA STRUCTURES
# ─────────────────────────────────────────────

@dataclass
class StockInput:
    """Raw data fed into the scoring engine."""
    symbol: str
    name: str

    # Price data
    close: float
    prev_close: float
    high_52w: float
    low_52w: float

    # Volume
    volume: float
    avg_volume_20d: float           # 20-day average volume

    # Technical indicators (pre-calculated)
    rsi_14: float                   # RSI (0–100)
    macd: float                     # MACD line value
    macd_signal: float              # MACD signal line
    ema_20: float                   # 20-day EMA
    ema_50: float                   # 50-day EMA
    ema_200: float                  # 200-day EMA
    atr_14: float                   # Average True Range (volatility)
    bb_upper: float                 # Bollinger Band upper
    bb_lower: float                 # Bollinger Band lower

    # Fundamental (optional, scored 5 if missing)
    pe_ratio: Optional[float] = None
    sector_pe: Optional[float] = None
    eps_growth_yoy: Optional[float] = None  # %

    # News/Event (pre-fetched sentiment score, -1 to +1)
    news_sentiment: float = 0.0     # -1=very negative, 0=neutral, +1=very positive
    event_impact: float = 0.0       # -1 to +1 (dividend+, IPO+, regulatory-)

    # Market context
    dsex_trend: float = 0.0         # -1 to +1 (overall market direction)


@dataclass
class ScoreBreakdown:
    """Per-factor scores (each 0–10) and their weighted contribution."""
    trend_strength: float
    volume_spike: float
    news_sentiment: float
    event_impact: float
    rsi_score: float
    macd_score: float
    ema_alignment: float
    volatility_score: float
    fundamental_score: float
    market_context: float


@dataclass
class StockScore:
    """Final output of the scoring engine."""
    symbol: str
    name: str

    # Core outputs
    total_score: float              # 0–10
    signal: str                     # STRONG_BUY / BUY / NEUTRAL / SELL / STRONG_SELL
    signal_strength: str            # STRONG / MODERATE / WEAK
    confidence: float               # 0–100 %
    confidence_label: str           # HIGH / MEDIUM / LOW

    # Risk
    risk_level: str                 # LOW / MEDIUM / HIGH / VERY_HIGH
    risk_score: float               # 0–10 (higher = riskier)

    # Breakdown
    breakdown: ScoreBreakdown

    # Meta
    price_change_pct: float
    volume_ratio: float             # current vol / avg vol


# ─────────────────────────────────────────────
#  WEIGHT CONFIGURATION
# ─────────────────────────────────────────────

WEIGHTS = {
    "trend_strength":   0.20,   # Price momentum & EMA alignment
    "volume_spike":     0.18,   # Volume vs average
    "news_sentiment":   0.15,   # News & social sentiment
    "event_impact":     0.12,   # Corporate events
    "rsi_score":        0.10,   # RSI signal
    "macd_score":       0.10,   # MACD crossover
    "ema_alignment":    0.08,   # EMA stack order
    "volatility_score": 0.04,   # ATR / Bollinger position
    "fundamental_score":0.02,   # PE vs sector
    "market_context":   0.01,   # DSEX index direction
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"


# ─────────────────────────────────────────────
#  FACTOR CALCULATORS  (each returns 0–10)
# ─────────────────────────────────────────────

def _score_trend_strength(d: StockInput) -> float:
    """
    Combines price change % with 52-week position.
    Strong uptrend near 52w high = 10; crash near 52w low = 0.
    """
    pct_change = (d.close - d.prev_close) / d.prev_close * 100

    # Normalise daily change: ±5% maps to 0–10
    change_score = _clamp((pct_change + 5) / 10 * 10, 0, 10)

    # 52-week position (0 = at low, 10 = at high)
    rng = d.high_52w - d.low_52w
    pos_score = _clamp((d.close - d.low_52w) / rng * 10, 0, 10) if rng > 0 else 5

    return round(change_score * 0.6 + pos_score * 0.4, 2)


def _score_volume_spike(d: StockInput) -> float:
    """
    Volume ratio vs 20-day average.
    3x volume = 10; below average = proportionally low.
    """
    if d.avg_volume_20d <= 0:
        return 5.0
    ratio = d.volume / d.avg_volume_20d
    # ratio 0→3+ maps to 0→10
    return round(_clamp(ratio / 3 * 10, 0, 10), 2)


def _score_news_sentiment(d: StockInput) -> float:
    """Sentiment -1..+1 → 0..10."""
    return round((d.news_sentiment + 1) / 2 * 10, 2)


def _score_event_impact(d: StockInput) -> float:
    """Event impact -1..+1 → 0..10."""
    return round((d.event_impact + 1) / 2 * 10, 2)


def _score_rsi(d: StockInput) -> float:
    """
    RSI scoring:
    <30 = oversold (bullish opportunity) → 8–10
    30–50 = mild bullish zone → 6–8
    50–70 = healthy uptrend → 6–7
    >70 = overbought (bearish risk) → 0–4
    """
    rsi = d.rsi_14
    if rsi < 20:   return 9.5
    if rsi < 30:   return 8.5
    if rsi < 40:   return 7.5
    if rsi < 50:   return 6.5
    if rsi < 60:   return 6.0
    if rsi < 70:   return 5.5
    if rsi < 80:   return 3.0
    return 1.5


def _score_macd(d: StockInput) -> float:
    """
    MACD vs Signal:
    Bullish crossover (MACD > signal) = high score.
    Divergence magnitude also considered.
    """
    diff = d.macd - d.macd_signal
    # Normalise: ±2 unit diff maps to 0–10
    score = _clamp((diff + 2) / 4 * 10, 0, 10)
    return round(score, 2)


def _score_ema_alignment(d: StockInput) -> float:
    """
    Perfect bull stack: price > EMA20 > EMA50 > EMA200 = 10
    Perfect bear stack: price < EMA20 < EMA50 < EMA200 = 0
    """
    conditions = [
        d.close  > d.ema_20,
        d.ema_20 > d.ema_50,
        d.ema_50 > d.ema_200,
        d.close  > d.ema_50,
        d.close  > d.ema_200,
    ]
    bull_count = sum(conditions)
    return round(bull_count / len(conditions) * 10, 2)


def _score_volatility(d: StockInput) -> float:
    """
    Low ATR relative to price = stable = better score.
    Position within Bollinger Bands also considered.
    """
    # ATR as % of price
    atr_pct = d.atr_14 / d.close * 100 if d.close > 0 else 5
    vol_score = _clamp(10 - atr_pct, 0, 10)  # higher atr% = lower score

    # Bollinger position: 0=lower band, 1=upper band
    bb_range = d.bb_upper - d.bb_lower
    if bb_range > 0:
        bb_pos = (d.close - d.bb_lower) / bb_range  # 0–1
        bb_score = bb_pos * 10  # near upper band = 10 (bullish)
    else:
        bb_score = 5.0

    return round(vol_score * 0.5 + bb_score * 0.5, 2)


def _score_fundamental(d: StockInput) -> float:
    """
    PE vs sector PE. Below sector = undervalued = bullish.
    Missing data returns neutral 5.
    """
    if d.pe_ratio is None or d.sector_pe is None or d.sector_pe == 0:
        return 5.0
    ratio = d.pe_ratio / d.sector_pe
    # ratio <0.7 = cheap → 8–10; ratio >1.5 = expensive → 0–3
    score = _clamp((2 - ratio) / 1.3 * 10, 0, 10)

    # EPS growth boost
    if d.eps_growth_yoy is not None:
        if d.eps_growth_yoy > 20:   score = min(10, score + 1.5)
        elif d.eps_growth_yoy > 0:  score = min(10, score + 0.5)
        elif d.eps_growth_yoy < 0:  score = max(0, score - 1.0)

    return round(score, 2)


def _score_market_context(d: StockInput) -> float:
    """DSEX trend: -1..+1 → 0..10."""
    return round((d.dsex_trend + 1) / 2 * 10, 2)


# ─────────────────────────────────────────────
#  RISK CALCULATOR
# ─────────────────────────────────────────────

def _calculate_risk(d: StockInput, total_score: float) -> tuple[str, float]:
    """
    Risk is separate from bullishness.
    A stock can be bullish AND high-risk.
    """
    atr_pct = d.atr_14 / d.close * 100 if d.close > 0 else 5
    vol_ratio = d.volume / d.avg_volume_20d if d.avg_volume_20d > 0 else 1

    risk = 0.0
    risk += min(atr_pct * 1.5, 4)      # high ATR = high risk (max 4 pts)
    risk += min(vol_ratio * 0.5, 2)    # unusual volume = more risk (max 2)
    if d.rsi_14 > 75 or d.rsi_14 < 25:
        risk += 2                       # extreme RSI = reversal risk
    if abs(d.news_sentiment) > 0.6:
        risk += 1                       # strong news = volatile
    if d.event_impact < -0.3:
        risk += 1                       # negative events

    risk = _clamp(risk, 0, 10)

    if   risk <= 2.5: label = "LOW"
    elif risk <= 5.0: label = "MEDIUM"
    elif risk <= 7.5: label = "HIGH"
    else:             label = "VERY_HIGH"

    return label, round(risk, 2)


# ─────────────────────────────────────────────
#  CONFIDENCE CALCULATOR
# ─────────────────────────────────────────────

def _calculate_confidence(
    d: StockInput,
    breakdown: ScoreBreakdown,
    total_score: float
) -> tuple[float, str]:
    """
    Confidence = how many factors AGREE with each other.
    High agreement + extreme score = high confidence.
    """
    scores = [
        breakdown.trend_strength,
        breakdown.volume_spike,
        breakdown.rsi_score,
        breakdown.macd_score,
        breakdown.ema_alignment,
    ]

    bullish = sum(1 for s in scores if s >= 6)
    bearish = sum(1 for s in scores if s <= 4)
    total   = len(scores)

    agreement = max(bullish, bearish) / total  # 0.4–1.0

    # Score extremity (how far from neutral 5)
    extremity = abs(total_score - 5) / 5       # 0–1

    confidence = (agreement * 0.6 + extremity * 0.4) * 100
    confidence = _clamp(confidence, 20, 95)

    if   confidence >= 75: label = "HIGH"
    elif confidence >= 50: label = "MEDIUM"
    else:                  label = "LOW"

    return round(confidence, 1), label


# ─────────────────────────────────────────────
#  SIGNAL CLASSIFIER
# ─────────────────────────────────────────────

def _classify_signal(score: float, confidence: float) -> tuple[str, str]:
    """Convert numeric score + confidence into signal labels."""
    if   score >= 8.0: signal = "STRONG_BUY"
    elif score >= 6.5: signal = "BUY"
    elif score >= 4.5: signal = "NEUTRAL"
    elif score >= 3.0: signal = "SELL"
    else:              signal = "STRONG_SELL"

    if   confidence >= 75: strength = "STRONG"
    elif confidence >= 50: strength = "MODERATE"
    else:                  strength = "WEAK"

    return signal, strength


# ─────────────────────────────────────────────
#  MAIN SCORING FUNCTION
# ─────────────────────────────────────────────

def score_stock(d: StockInput) -> StockScore:
    """
    Master function: takes raw StockInput → returns complete StockScore.
    """
    # 1. Calculate individual factor scores
    breakdown = ScoreBreakdown(
        trend_strength   = _score_trend_strength(d),
        volume_spike     = _score_volume_spike(d),
        news_sentiment   = _score_news_sentiment(d),
        event_impact     = _score_event_impact(d),
        rsi_score        = _score_rsi(d),
        macd_score       = _score_macd(d),
        ema_alignment    = _score_ema_alignment(d),
        volatility_score = _score_volatility(d),
        fundamental_score= _score_fundamental(d),
        market_context   = _score_market_context(d),
    )

    # 2. Weighted total
    total = (
        breakdown.trend_strength    * WEIGHTS["trend_strength"]   +
        breakdown.volume_spike      * WEIGHTS["volume_spike"]     +
        breakdown.news_sentiment    * WEIGHTS["news_sentiment"]   +
        breakdown.event_impact      * WEIGHTS["event_impact"]     +
        breakdown.rsi_score         * WEIGHTS["rsi_score"]        +
        breakdown.macd_score        * WEIGHTS["macd_score"]       +
        breakdown.ema_alignment     * WEIGHTS["ema_alignment"]    +
        breakdown.volatility_score  * WEIGHTS["volatility_score"] +
        breakdown.fundamental_score * WEIGHTS["fundamental_score"]+
        breakdown.market_context    * WEIGHTS["market_context"]
    )
    total = round(_clamp(total, 0, 10), 2)

    # 3. Risk
    risk_label, risk_score = _calculate_risk(d, total)

    # 4. Confidence
    confidence, conf_label = _calculate_confidence(d, breakdown, total)

    # 5. Signal
    signal, strength = _classify_signal(total, confidence)

    # 6. Derived metrics
    price_change_pct = round((d.close - d.prev_close) / d.prev_close * 100, 2)
    volume_ratio = round(d.volume / d.avg_volume_20d, 2) if d.avg_volume_20d > 0 else 1.0

    return StockScore(
        symbol          = d.symbol,
        name            = d.name,
        total_score     = total,
        signal          = signal,
        signal_strength = strength,
        confidence      = confidence,
        confidence_label= conf_label,
        risk_level      = risk_label,
        risk_score      = risk_score,
        breakdown       = breakdown,
        price_change_pct= price_change_pct,
        volume_ratio    = volume_ratio,
    )


def score_batch(stocks: list[StockInput]) -> list[StockScore]:
    """Score a list of stocks and return sorted by total_score descending."""
    results = [score_stock(s) for s in stocks]
    return sorted(results, key=lambda x: x.total_score, reverse=True)


def export_json(scores: list[StockScore]) -> str:
    """Serialize scored stocks to JSON."""
    def to_dict(s: StockScore):
        d = asdict(s)
        return d
    return json.dumps([to_dict(s) for s in scores], indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────

def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


# ─────────────────────────────────────────────
#  DEMO / TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Sample stocks (replace with real data from DSE API)
    samples = [
        StockInput(
            symbol="SQURPHARMA", name="Square Pharmaceuticals",
            close=235.50, prev_close=228.00,
            high_52w=270.00, low_52w=190.00,
            volume=850_000, avg_volume_20d=400_000,
            rsi_14=58, macd=2.1, macd_signal=1.4,
            ema_20=230, ema_50=220, ema_200=210,
            atr_14=5.2, bb_upper=245, bb_lower=215,
            pe_ratio=18, sector_pe=22, eps_growth_yoy=15,
            news_sentiment=0.6, event_impact=0.3, dsex_trend=0.2,
        ),
        StockInput(
            symbol="BEXIMCO", name="Beximco Limited",
            close=44.20, prev_close=47.50,
            high_52w=68.00, low_52w=38.00,
            volume=1_200_000, avg_volume_20d=900_000,
            rsi_14=38, macd=-0.8, macd_signal=-0.2,
            ema_20=46, ema_50=52, ema_200=55,
            atr_14=2.1, bb_upper=50, bb_lower=40,
            pe_ratio=25, sector_pe=20, eps_growth_yoy=-8,
            news_sentiment=-0.4, event_impact=-0.2, dsex_trend=0.1,
        ),
        StockInput(
            symbol="GRAMEENPHONE", name="Grameenphone Ltd",
            close=310.00, prev_close=305.00,
            high_52w=340.00, low_52w=270.00,
            volume=320_000, avg_volume_20d=280_000,
            rsi_14=62, macd=1.5, macd_signal=1.0,
            ema_20=305, ema_50=295, ema_200=285,
            atr_14=7.0, bb_upper=325, bb_lower=290,
            pe_ratio=14, sector_pe=18, eps_growth_yoy=10,
            news_sentiment=0.3, event_impact=0.5, dsex_trend=0.2,
        ),
    ]

    results = score_batch(samples)

    print("=" * 65)
    print("  DSEX PRO — ADVANCED SCORING ENGINE  (Step 1)")
    print("=" * 65)

    for r in results:
        print(f"\n{'─'*60}")
        print(f"  {r.symbol:20s} | Score: {r.total_score}/10 | {r.signal}")
        print(f"  Signal Strength : {r.signal_strength}")
        print(f"  Confidence      : {r.confidence}% ({r.confidence_label})")
        print(f"  Risk Level      : {r.risk_level} ({r.risk_score}/10)")
        print(f"  Price Change    : {r.price_change_pct:+.2f}%")
        print(f"  Volume Ratio    : {r.volume_ratio}x avg")
        print(f"\n  Factor Breakdown:")
        b = r.breakdown
        factors = [
            ("Trend Strength",    b.trend_strength,    WEIGHTS["trend_strength"]),
            ("Volume Spike",      b.volume_spike,      WEIGHTS["volume_spike"]),
            ("News Sentiment",    b.news_sentiment,    WEIGHTS["news_sentiment"]),
            ("Event Impact",      b.event_impact,      WEIGHTS["event_impact"]),
            ("RSI Signal",        b.rsi_score,         WEIGHTS["rsi_score"]),
            ("MACD",              b.macd_score,        WEIGHTS["macd_score"]),
            ("EMA Alignment",     b.ema_alignment,     WEIGHTS["ema_alignment"]),
            ("Volatility",        b.volatility_score,  WEIGHTS["volatility_score"]),
            ("Fundamentals",      b.fundamental_score, WEIGHTS["fundamental_score"]),
            ("Market Context",    b.market_context,    WEIGHTS["market_context"]),
        ]
        for name, score, weight in factors:
            bar = "█" * int(score) + "░" * (10 - int(score))
            print(f"    {name:18s} {bar} {score:4.1f}/10  (wt:{weight:.0%})")

    print(f"\n{'='*65}")
    print(f"  JSON export preview (first stock):")
    print(export_json(results[:1]))
>>>>>>> ba7e25db86fb7ea4f7076427091104d359f89ae4
