print("🔥 NEW VERSION RUNNING")

import os
import json
from datetime import datetime

from data_scraper import get_dse_data, get_price_history
from database import save_daily_data
from indicators import calculate_indicators
from scoring_engine import StockInput, score_batch
from prediction_engine import generate_predictions
from high_impact import detect_high_impact
from ai_explainer import generate_explanation


# =========================
# SAFE FUNCTION
# =========================
def safe_value(val, default=0):
    try:
        return float(val)
    except:
        return default


# =========================
# SAVE OUTPUT (FIXED PATH ✅)
# =========================
def save_output(results):
    # 🔥 ABSOLUTE PATH FIX (IMPORTANT)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"📁 OUTPUT DIR: {OUTPUT_DIR}")

    # DATE
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().isoformat()

    # FILE PATHS
    daily_file = os.path.join(OUTPUT_DIR, f"{today}.json")
    latest_file = os.path.join(OUTPUT_DIR, "latest.json")

    bullish_pred, bearish_pred = generate_predictions(results)

    data = {
        "date": today,
        "timestamp": timestamp,
        "top_bullish": bullish_pred,
        "top_bearish": bearish_pred,
        "high_impact": [],
        "all_stocks": []
    }

    for r in results:
        data["all_stocks"].append({
            "symbol": r.symbol,
            "score": r.total_score,
            "signal": r.signal,
            "confidence": r.confidence,
            "risk": r.risk_level,
            "price_change_pct": r.price_change_pct,
            "volume_ratio": r.volume_ratio,
            "explanation": generate_explanation(r)
        })

        impact_score, reasons = detect_high_impact(r)

        if impact_score >= 2:
            data["high_impact"].append({
                "symbol": r.symbol,
                "impact_score": impact_score,
                "reasons": reasons,
                "explanation": generate_explanation(r)
            })

    # SORT HIGH IMPACT
    data["high_impact"] = sorted(
        data["high_impact"],
        key=lambda x: x["impact_score"],
        reverse=True
    )[:20]

    # SAVE DAILY
    with open(daily_file, "w") as f:
        json.dump(data, f, indent=2)

    # SAVE LATEST
    with open(latest_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Saved daily: {daily_file}")
    print(f"✅ Updated latest: {latest_file}")


# =========================
# MAIN
# =========================
def main():
    print("🚀 Starting system...\n")

    raw_data = get_dse_data()

    if not raw_data:
        print("❌ No data fetched")
        return

    print(f"📊 DSE data fetched: {len(raw_data)} stocks")

    save_daily_data(raw_data)

    stocks = []

    for s in raw_data:
        try:
            symbol = s["symbol"]
            close = safe_value(s["close"])
            prev_close = safe_value(s["prev_close"])
            volume = safe_value(s["volume"])

            if close == 0:
                continue

            prices = get_price_history(symbol)

            if not prices or len(prices) < 20:
                continue

            ind = calculate_indicators(prices)

            stock = StockInput(
                symbol=symbol,
                name=symbol,

                close=close,
                prev_close=prev_close,
                high_52w=max(prices),
                low_52w=min(prices),

                volume=volume,
                avg_volume_20d=volume if volume > 0 else 1,

                rsi_14=ind["rsi"],
                macd=ind["macd"],
                macd_signal=ind["macd_signal"],
                ema_20=ind["ema20"],
                ema_50=ind["ema50"],
                ema_200=ind["ema200"],
                atr_14=ind["atr"],
                bb_upper=ind["bb_upper"],
                bb_lower=ind["bb_lower"],

                pe_ratio=15,
                sector_pe=20,
                eps_growth_yoy=5,

                news_sentiment=0,
                event_impact=0,
                dsex_trend=0
            )

            stocks.append(stock)

        except Exception as e:
            print(f"❌ Error {s.get('symbol','?')}: {e}")
            continue

    print(f"\n📊 Valid stocks for scoring: {len(stocks)}")

    if not stocks:
        print("❌ No valid stocks for scoring")
        return

    print("\n⚙️ Scoring stocks...\n")

    results = score_batch(stocks)

    print(f"📊 Total scored: {len(results)}")

    if not results:
        print("❌ No results after scoring")
        return

    # TOP 20
    print("\n🔥 TOP STOCKS 🔥\n")

    for r in results[:20]:
        tag = "🔥" if r.total_score >= 5 else "⚠️" if r.total_score >= 3 else "❌"
        print(f"{tag} {r.symbol} | Score: {r.total_score} | Signal: {r.signal}")

    save_output(results)

    print("\n✅ DONE\n")


# RUN
if __name__ == "__main__":
    main()