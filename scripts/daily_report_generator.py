"""
DSEX PRO — Step 6: Upgraded daily-report.json Generator
=========================================================
Produces the master JSON that powers:
  - GitHub Actions daily pipeline
  - Chrome Extension (Step 7)
  - Alert System (Step 8)

Schema includes ALL data from Steps 1-5:
  - Scoring breakdown
  - AI analysis & reasoning
  - Event detection
  - Stock rating (grade, investment)
  - Multi-timeframe signals
  - Price levels
  - Alert flags
"""

import json
from datetime import date, datetime


def build_daily_report(stocks: list) -> dict:
    """
    stocks: list of fully-enriched stock dicts (all steps combined)
    Returns the complete daily-report JSON structure.
    """
    today = date.today().isoformat()
    now   = datetime.now().isoformat()

    # Market-level aggregates
    scores    = [s["scoring"]["total_score"] for s in stocks]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 5.0
    bull      = [s for s in stocks if s["scoring"]["signal"] in ("STRONG_BUY","BUY")]
    bear      = [s for s in stocks if s["scoring"]["signal"] in ("STRONG_SELL","SELL")]
    urgent    = [s for s in stocks if s["events"]["has_urgent_event"]]

    market_mood = (
        "VERY_BULLISH" if avg_score >= 7.5 else
        "BULLISH"      if avg_score >= 6.0 else
        "BEARISH"      if avg_score <= 4.0 else
        "VERY_BEARISH" if avg_score <= 2.5 else
        "NEUTRAL"
    )

    # Top lists
    by_score = sorted(stocks, key=lambda s: s["scoring"]["total_score"], reverse=True)
    by_rating= sorted(stocks, key=lambda s: s["rating"]["rating"], reverse=True)
    by_event = sorted(stocks, key=lambda s: abs(s["events"]["composite_impact"]), reverse=True)
    by_conf  = sorted(stocks, key=lambda s: s["scoring"]["confidence"], reverse=True)

    return {
        "_meta": {
            "version":      "3.0.0",
            "generated_at": now,
            "report_date":  today,
            "schema":       "DSEX_PRO_FULL",
            "steps":        ["scoring","ai_analysis","events","rating","multi_timeframe"],
            "total_stocks": len(stocks),
        },
        "market_summary": {
            "date":            today,
            "market_mood":     market_mood,
            "avg_score":       avg_score,
            "bullish_count":   len(bull),
            "bearish_count":   len(bear),
            "neutral_count":   len(stocks) - len(bull) - len(bear),
            "urgent_alerts":   len(urgent),
            "high_confidence": len([s for s in stocks if s["scoring"]["confidence"] >= 70]),
        },
        "top_20_bullish": [
            _mini(s) for s in by_score
            if s["scoring"]["signal"] in ("STRONG_BUY","BUY","NEUTRAL")
        ][:20],
        "top_20_bearish": [
            _mini(s) for s in reversed(by_score)
            if s["scoring"]["signal"] in ("STRONG_SELL","SELL","NEUTRAL")
        ][:20],
        "top_20_high_impact": [
            _mini(s) for s in by_event
        ][:20],
        "top_20_by_rating": [
            _mini(s) for s in by_rating
        ][:20],
        "urgent_alerts": [
            {
                "symbol":   s["symbol"],
                "alert":    s["events"]["alert_message"],
                "urgency":  "HIGH",
                "signal":   s["scoring"]["signal"],
                "rating":   s["rating"]["rating"],
            }
            for s in urgent
        ],
        "stocks": stocks,
        "weekly_outlook": _build_weekly(stocks, today, market_mood),
    }


def _mini(s: dict) -> dict:
    """Compact summary entry for top-20 lists."""
    return {
        "symbol":      s["symbol"],
        "name":        s["name"],
        "score":       s["scoring"]["total_score"],
        "signal":      s["scoring"]["signal"],
        "grade":       s["rating"]["grade"],
        "investment":  s["rating"]["investment"],
        "confidence":  s["scoring"]["confidence"],
        "risk":        s["scoring"]["risk_level"],
        "next_day":    s["multi_timeframe"]["next_day"]["signal"],
        "next_week":   s["multi_timeframe"]["next_week"]["signal"],
        "event_impact":s["events"]["composite_impact"],
        "headline":    s["ai_analysis"]["headline"],
    }


def _build_weekly(stocks, today, mood):
    bull = [s for s in stocks if s["multi_timeframe"]["next_week"]["signal"] in ("STRONG_BUY","BUY")]
    bear = [s for s in stocks if s["multi_timeframe"]["next_week"]["signal"] in ("STRONG_SELL","SELL")]
    return {
        "week_start":     today,
        "market_mood":    mood,
        "top_bullish":    [s["symbol"] for s in sorted(bull, key=lambda x: x["scoring"]["total_score"], reverse=True)[:5]],
        "top_bearish":    [s["symbol"] for s in sorted(bear, key=lambda x: x["scoring"]["total_score"])[:5]],
        "avg_confidence": round(sum(s["scoring"]["confidence"] for s in stocks)/len(stocks), 1) if stocks else 50,
        "narrative":      _weekly_narrative(stocks, mood),
    }


def _weekly_narrative(stocks, mood):
    n = len(stocks)
    bull_pct = round(len([s for s in stocks if "BUY" in s["scoring"]["signal"]]) / n * 100)
    top = sorted(stocks, key=lambda s: s["scoring"]["total_score"], reverse=True)[0]
    bot = sorted(stocks, key=lambda s: s["scoring"]["total_score"])[0]
    return (
        f"DSEX weekly outlook is {mood}. "
        f"{bull_pct}% of monitored stocks show bullish or strong-bullish signals. "
        f"Top pick: {top['symbol']} ({top['scoring']['total_score']}/10). "
        f"Avoid: {bot['symbol']} ({bot['scoring']['total_score']}/10). "
        f"Event calendar is active — watch dividend and earnings announcements this week."
    )


def stock_to_full_dict(symbol, name, scored, ai, events, rating, mtf) -> dict:
    """Assemble all step outputs into one unified stock dict."""
    return {
        "symbol": symbol,
        "name":   name,
        # Step 1
        "scoring": {
            "total_score":     scored["total_score"],
            "signal":          scored["signal"],
            "signal_strength": scored["signal_strength"],
            "confidence":      scored["confidence"],
            "confidence_label":scored["confidence_label"],
            "risk_level":      scored["risk_level"],
            "risk_score":      scored["risk_score"],
            "price_change_pct":scored["price_change_pct"],
            "volume_ratio":    scored["volume_ratio"],
            "breakdown":       scored["breakdown"],
        },
        # Step 2
        "ai_analysis": {
            "headline":    ai.get("headline",""),
            "outlook_tag": ai.get("outlook_tag","NEUTRAL"),
            "summary":     ai.get("summary",""),
            "key_drivers": ai.get("drivers",[]),
            "risk_note":   ai.get("risk_note",""),
            "action_note": ai.get("action_note",""),
        },
        # Step 3
        "events": {
            "total_events":     events["total"],
            "composite_impact": events["composite"],
            "impact_label":     events["label"],
            "has_urgent_event": events["urgent"],
            "alert_message":    events["alert"],
            "event_list":       [
                {
                    "type":    e["type"],
                    "title":   e["title"],
                    "impact":  e["impact"],
                    "urgency": e["urgency"],
                    "date":    e["date"],
                }
                for e in events.get("events", [])
            ],
        },
        # Step 4
        "rating": {
            "rating":           rating["rating"],
            "grade":            rating["grade"],
            "grade_label":      rating["grade_label"],
            "investment":       rating["investment"],
            "risk_level":       rating["risk_level"],
            "confidence":       rating["confidence"],
            "confidence_label": rating["confidence_label"],
            "component_scores": {
                "technical":    rating["tech"],
                "fundamental":  rating["fund"],
                "event":        rating["event"],
                "sentiment":    rating["sent"],
            },
            "horizon":          rating["horizon"],
            "stop_loss_note":   rating["stopNote"],
            "key_positives":    rating["pos"],
            "key_negatives":    rating["neg"],
            "rationale":        rating["rationale"],
        },
        # Step 5
        "multi_timeframe": {
            "master_signal":     mtf["master_signal"],
            "confluence_score":  mtf["confluence_score"],
            "confluence_label":  mtf["confluence_label"],
            "market_phase":      mtf["market_phase"],
            "volatility_regime": mtf["volatility_regime"],
            "next_day": {
                "signal":        mtf["next_day"]["signal"],
                "confidence":    mtf["next_day"]["confidence"],
                "expected_move": mtf["next_day"]["expected_move"],
                "key_trigger":   mtf["next_day"]["key_trigger"],
                "bias":          mtf["next_day"]["bias"],
            },
            "next_week": {
                "signal":        mtf["next_week"]["signal"],
                "confidence":    mtf["next_week"]["confidence"],
                "expected_move": mtf["next_week"]["expected_move"],
                "key_trigger":   mtf["next_week"]["key_trigger"],
                "bias":          mtf["next_week"]["bias"],
            },
            "price_levels": {
                "support_1":    mtf["levels"]["support_1"],
                "support_2":    mtf["levels"]["support_2"],
                "resistance_1": mtf["levels"]["resistance_1"],
                "resistance_2": mtf["levels"]["resistance_2"],
                "stop_loss":    mtf["levels"]["stop_loss"],
                "target_1":     mtf["levels"]["target_1"],
                "target_2":     mtf["levels"]["target_2"],
                "risk_reward":  mtf["levels"]["risk_reward"],
            },
        },
        # Alert flags (Step 8 triggers)
        "alert_flags": {
            "strong_signal":   scored["total_score"] >= 8.0 or scored["total_score"] <= 2.0,
            "high_confidence": scored["confidence"] >= 75,
            "urgent_event":    events["urgent"],
            "volume_breakout": scored["volume_ratio"] >= 2.5,
            "mtf_aligned":     mtf["confluence_label"] in ("FULLY_ALIGNED","MOSTLY_ALIGNED"),
            "grade_change":    False,  # set by GitHub Action when grade improves/drops
        },
    }
