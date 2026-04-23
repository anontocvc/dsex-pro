"""
DSEX PRO — Step 5: Multi-Timeframe Analysis Engine
====================================================
Generates:
  - Next Day Signal    (intraday momentum + gap analysis)
  - Next Week Outlook  (trend continuation + event calendar)
  - Key price levels   (support, resistance, stop, target)
  - Timeframe confluence score
"""

from dataclasses import dataclass, asdict, field
from typing import Optional
import json


@dataclass
class PriceLevels:
    support_1:    float   # nearest support
    support_2:    float   # second support
    resistance_1: float   # nearest resistance
    resistance_2: float   # second resistance
    stop_loss:    float   # calculated stop
    target_1:     float   # first target
    target_2:     float   # second target
    risk_reward:  float   # R:R ratio


@dataclass
class TimeframeSignal:
    timeframe:      str     # "NEXT_DAY" | "NEXT_WEEK"
    signal:         str     # STRONG_BUY / BUY / NEUTRAL / SELL / STRONG_SELL
    confidence:     float   # 0-100
    expected_move:  str     # e.g. "+1.5% to +3.0%"
    key_trigger:    str     # what would confirm or invalidate
    bias:           str     # BULLISH / NEUTRAL / BEARISH


@dataclass
class MultiTimeframeAnalysis:
    symbol:         str
    name:           str
    current_price:  float

    # Timeframe signals
    next_day:       TimeframeSignal
    next_week:      TimeframeSignal

    # Price levels
    levels:         PriceLevels

    # Confluence
    confluence_score:  float    # 0-10: how much day+week agree
    confluence_label:  str      # ALIGNED / MIXED / CONFLICTED
    master_signal:     str      # combined verdict

    # Context
    volatility_regime: str      # LOW_VOL / NORMAL / HIGH_VOL / EXTREME
    market_phase:      str      # BREAKOUT / TRENDING / CONSOLIDATING / REVERSING


# ─── PRICE LEVEL CALCULATOR ───────────────────────────────

def calc_levels(close: float, atr: float, ema20: float, ema50: float,
                bb_upper: float, bb_lower: float, signal: str) -> PriceLevels:
    """ATR-based dynamic support/resistance + targets."""
    # Support: EMA20 and EMA50 (or ATR bands below)
    s1 = round(max(ema20, close - atr * 1.5), 2)
    s2 = round(max(ema50, close - atr * 3.0), 2)

    # Resistance: Bollinger upper or ATR multiples above
    r1 = round(min(bb_upper, close + atr * 1.5), 2)
    r2 = round(close + atr * 3.0, 2)

    # Stop loss: 1.5-2x ATR below nearest support
    stop = round(s1 - atr * 1.2, 2)

    # Targets: based on signal direction
    if "BUY" in signal:
        t1 = round(close + atr * 2.0, 2)
        t2 = round(close + atr * 4.0, 2)
    elif "SELL" in signal:
        t1 = round(close - atr * 2.0, 2)
        t2 = round(close - atr * 4.0, 2)
    else:
        t1 = r1
        t2 = s1

    risk   = abs(close - stop)
    reward = abs(close - t1)
    rr     = round(reward / risk, 2) if risk > 0 else 1.0

    return PriceLevels(s1, s2, r1, r2, stop, t1, t2, rr)


# ─── NEXT-DAY SIGNAL ─────────────────────────────────────

def calc_next_day(scored: dict, raw: dict) -> TimeframeSignal:
    """
    Short-term (1-day) signal driven by:
    - RSI momentum
    - Volume spike (breakout confirmation)
    - MACD crossover proximity
    - Price vs BB bands
    - Gap potential (close vs EMA20)
    """
    b    = scored["breakdown"]
    rsi  = raw.get("rsi", 50)
    vr   = scored["volume_ratio"]
    pct  = scored["price_change_pct"]
    close= raw.get("close", 100)
    e20  = raw.get("e20", close)
    bbu  = raw.get("bbu", close * 1.02)
    bbl  = raw.get("bbl", close * 0.98)

    score = 0.0

    # RSI momentum
    if rsi < 35:    score += 2.5   # oversold bounce likely
    elif rsi < 50:  score += 1.0
    elif rsi < 65:  score += 0.5
    elif rsi < 75:  score -= 0.5
    else:           score -= 2.0   # overbought, pullback risk

    # Volume confirmation
    if vr >= 2.5:   score += 2.0
    elif vr >= 1.5: score += 1.0
    elif vr < 0.7:  score -= 1.0

    # MACD crossover
    macd_diff = raw.get("macd", 0) - raw.get("msig", 0)
    if macd_diff > 0.5:   score += 1.5
    elif macd_diff > 0:   score += 0.5
    elif macd_diff < -0.5: score -= 1.5
    else:                  score -= 0.5

    # Bollinger position
    bb_range = bbu - bbl
    if bb_range > 0:
        bb_pos = (close - bbl) / bb_range  # 0-1
        if bb_pos < 0.2:   score += 1.5    # near lower band → bounce
        elif bb_pos > 0.8: score -= 1.0    # near upper → fading

    # Recent momentum
    if pct > 3:    score += 1.0
    elif pct > 1:  score += 0.5
    elif pct < -3: score -= 1.0
    elif pct < -1: score -= 0.5

    # Normalize to 0-10 then convert to signal
    total = max(0, min(10, score + 5))

    if   total >= 8.0: sig, bias = "STRONG_BUY",  "BULLISH"
    elif total >= 6.5: sig, bias = "BUY",          "BULLISH"
    elif total >= 4.5: sig, bias = "NEUTRAL",      "NEUTRAL"
    elif total >= 3.0: sig, bias = "SELL",         "BEARISH"
    else:              sig, bias = "STRONG_SELL",  "BEARISH"

    conf = min(90, abs(total - 5) / 5 * 70 + 30)

    # Expected move based on ATR
    atr = raw.get("atr", close * 0.02)
    atr_pct = atr / close * 100
    if "BUY" in sig:
        move = f"+{atr_pct*0.8:.1f}% to +{atr_pct*1.8:.1f}%"
    elif "SELL" in sig:
        move = f"-{atr_pct*0.8:.1f}% to -{atr_pct*1.8:.1f}%"
    else:
        move = f"-{atr_pct*0.5:.1f}% to +{atr_pct*0.5:.1f}%"

    # Trigger condition
    if "BUY" in sig:
        trigger = f"Hold above BDT {round(close * 0.99, 1)} with volume > 1.2x avg"
    elif "SELL" in sig:
        trigger = f"Break below BDT {round(close * 0.985, 1)} confirms downside"
    else:
        trigger = f"Watch for volume breakout above BDT {round(close * 1.015, 1)}"

    return TimeframeSignal(
        timeframe="NEXT_DAY", signal=sig,
        confidence=round(conf, 1), expected_move=move,
        key_trigger=trigger, bias=bias
    )


# ─── NEXT-WEEK SIGNAL ────────────────────────────────────

def calc_next_week(scored: dict, raw: dict, event_composite: float = 0.0) -> TimeframeSignal:
    """
    Medium-term (1-week) signal driven by:
    - EMA alignment (trend structure)
    - Fundamental score
    - Event calendar impact
    - 52-week position
    - Overall scoring engine output
    """
    b     = scored["breakdown"]
    total = scored["total_score"]
    close = raw.get("close", 100)
    h52   = raw.get("h52", close * 1.3)
    l52   = raw.get("l52", close * 0.7)

    score = 0.0

    # EMA alignment is the strongest weekly indicator
    ema_score = b.get("ema_alignment", 5)
    score += (ema_score - 5) * 0.6

    # Fundamental backdrop
    fund = b.get("fundamental_score", 5)
    score += (fund - 5) * 0.3

    # 52-week position momentum
    rng = h52 - l52
    if rng > 0:
        pos = (close - l52) / rng
        if pos > 0.8:   score += 1.5    # near 52w high = momentum
        elif pos > 0.6: score += 0.5
        elif pos < 0.2: score -= 1.0    # near 52w low = downtrend
        elif pos < 0.4: score -= 0.3

    # Event calendar boost/drag
    score += event_composite * 2.0

    # Overall score as tiebreaker
    score += (total - 5) * 0.2

    total_w = max(0, min(10, score + 5))

    if   total_w >= 8.0: sig, bias = "STRONG_BUY",  "BULLISH"
    elif total_w >= 6.5: sig, bias = "BUY",          "BULLISH"
    elif total_w >= 4.5: sig, bias = "NEUTRAL",      "NEUTRAL"
    elif total_w >= 3.0: sig, bias = "SELL",         "BEARISH"
    else:                sig, bias = "STRONG_SELL",  "BEARISH"

    conf = min(88, abs(total_w - 5) / 5 * 65 + 25)

    atr = raw.get("atr", close * 0.02)
    atr_pct = atr / close * 100
    if "BUY" in sig:
        move = f"+{atr_pct*2.0:.1f}% to +{atr_pct*4.5:.1f}%"
    elif "SELL" in sig:
        move = f"-{atr_pct*2.0:.1f}% to -{atr_pct*4.5:.1f}%"
    else:
        move = f"±{atr_pct*1.5:.1f}% (range-bound)"

    e20 = raw.get("e20", close)
    e50 = raw.get("e50", close * 0.95)
    if "BUY" in sig:
        trigger = f"Weekly close above BDT {round(max(e20, close)*1.01, 1)} confirms"
    elif "SELL" in sig:
        trigger = f"Break below EMA50 (BDT {round(e50, 1)}) accelerates decline"
    else:
        trigger = f"Range: BDT {round(e50,1)} – {round(raw.get('bbu', close*1.05),1)}"

    return TimeframeSignal(
        timeframe="NEXT_WEEK", signal=sig,
        confidence=round(conf, 1), expected_move=move,
        key_trigger=trigger, bias=bias
    )


# ─── CONFLUENCE + MARKET PHASE ───────────────────────────

def calc_confluence(day: TimeframeSignal, week: TimeframeSignal) -> tuple:
    sig_rank = {"STRONG_BUY": 4, "BUY": 3, "NEUTRAL": 2, "SELL": 1, "STRONG_SELL": 0}
    d = sig_rank[day.signal]
    w = sig_rank[week.signal]
    diff = abs(d - w)

    score = round(10 - diff * 2.5, 1)
    score = max(0, min(10, score))

    if diff == 0:   label = "FULLY_ALIGNED"
    elif diff <= 1: label = "MOSTLY_ALIGNED"
    elif diff == 2: label = "MIXED"
    else:           label = "CONFLICTED"

    # Master signal: week dominates, day modifies
    if day.bias == week.bias:
        master = week.signal
    elif week.bias == "BULLISH":
        master = "BUY" if day.bias != "BEARISH" else "NEUTRAL"
    elif week.bias == "BEARISH":
        master = "SELL" if day.bias != "BULLISH" else "NEUTRAL"
    else:
        master = "NEUTRAL"

    return score, label, master


def calc_vol_regime(atr_pct: float) -> str:
    if   atr_pct < 1.0: return "LOW_VOL"
    elif atr_pct < 2.5: return "NORMAL"
    elif atr_pct < 5.0: return "HIGH_VOL"
    else:               return "EXTREME"


def calc_market_phase(scored: dict, raw: dict) -> str:
    b     = scored["breakdown"]
    ema_a = b.get("ema_alignment", 5)
    vol   = b.get("volume_spike", 5)
    rsi   = raw.get("rsi", 50)
    pct   = scored["price_change_pct"]

    if ema_a >= 8 and vol >= 7:   return "BREAKOUT"
    if ema_a >= 6 and abs(pct) > 1.5: return "TRENDING"
    if 40 < rsi < 60 and vol < 5: return "CONSOLIDATING"
    if ema_a <= 3 and pct < -2:   return "REVERSING"
    return "TRENDING"


# ─── MASTER FUNCTION ─────────────────────────────────────

def build_mtf(scored: dict, raw: dict, event_composite: float = 0.0) -> MultiTimeframeAnalysis:
    close  = raw.get("close", 100)
    atr    = raw.get("atr", close * 0.02)
    atr_pct = atr / close * 100

    day    = calc_next_day(scored, raw)
    week   = calc_next_week(scored, raw, event_composite)
    conf_s, conf_l, master = calc_confluence(day, week)
    levels = calc_levels(close, atr, raw.get("e20", close),
                         raw.get("e50", close*0.95),
                         raw.get("bbu", close*1.02),
                         raw.get("bbl", close*0.98),
                         master)

    return MultiTimeframeAnalysis(
        symbol           = scored["symbol"],
        name             = scored["name"],
        current_price    = close,
        next_day         = day,
        next_week        = week,
        levels           = levels,
        confluence_score = conf_s,
        confluence_label = conf_l,
        master_signal    = master,
        volatility_regime= calc_vol_regime(atr_pct),
        market_phase     = calc_market_phase(scored, raw),
    )


def build_mtf_batch(scored_list, raw_list, event_composites) -> list:
    return [build_mtf(s, r, e) for s, r, e in zip(scored_list, raw_list, event_composites)]


if __name__ == "__main__":
    # Quick test
    mock_scored = {
        "symbol": "SQURPHARMA", "name": "Square Pharmaceuticals",
        "total_score": 7.32, "signal": "BUY",
        "confidence": 78.6, "confidence_label": "HIGH",
        "risk_level": "MEDIUM", "risk_score": 4.37,
        "price_change_pct": 3.29, "volume_ratio": 2.12,
        "breakdown": {"trend_strength":7.25,"volume_spike":7.08,"news_sentiment":8.0,
                      "event_impact":6.5,"rsi_score":6.0,"macd_score":6.75,
                      "ema_alignment":10.0,"volatility_score":7.31,
                      "fundamental_score":9.59,"market_context":6.0},
    }
    mock_raw = {"close":235.5,"prev":228,"h52":270,"l52":190,"rsi":58,
                "macd":2.1,"msig":1.4,"e20":230,"e50":220,"e200":210,
                "atr":5.2,"bbu":245,"bbl":215,"vol":850000,"avg":400000}

    mtf = build_mtf(mock_scored, mock_raw, event_composite=0.565)

    print("=" * 60)
    print(f"  MULTI-TIMEFRAME: {mtf.symbol}")
    print("=" * 60)
    print(f"  Market Phase    : {mtf.market_phase}")
    print(f"  Volatility      : {mtf.volatility_regime}")
    print(f"  Master Signal   : {mtf.master_signal}")
    print(f"  Confluence      : {mtf.confluence_score}/10 ({mtf.confluence_label})")
    print(f"\n  NEXT DAY:")
    print(f"    Signal  : {mtf.next_day.signal} ({mtf.next_day.confidence}% conf)")
    print(f"    Move    : {mtf.next_day.expected_move}")
    print(f"    Trigger : {mtf.next_day.key_trigger}")
    print(f"\n  NEXT WEEK:")
    print(f"    Signal  : {mtf.next_week.signal} ({mtf.next_week.confidence}% conf)")
    print(f"    Move    : {mtf.next_week.expected_move}")
    print(f"    Trigger : {mtf.next_week.key_trigger}")
    print(f"\n  PRICE LEVELS:")
    print(f"    Support  : {mtf.levels.support_1} / {mtf.levels.support_2}")
    print(f"    Resistance: {mtf.levels.resistance_1} / {mtf.levels.resistance_2}")
    print(f"    Stop Loss: {mtf.levels.stop_loss}")
    print(f"    Targets  : {mtf.levels.target_1} / {mtf.levels.target_2}")
    print(f"    R:R Ratio: {mtf.levels.risk_reward}:1")
