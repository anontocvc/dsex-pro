<<<<<<< HEAD
import os
import pandas as pd

from indicators import apply_indicators
from scoring_engine import score_stock


DATA_PATH = "data/history"


# ==============================
# LOAD DATA
# ==============================
def load_stock_data():
    stocks = {}

    for file in os.listdir(DATA_PATH):
        if file.endswith(".csv"):
            symbol = file.replace(".csv", "")

            path = os.path.join(DATA_PATH, file)

            try:
                df = pd.read_csv(path)

                # 🔥 REQUIRED CHECK
                if len(df) < 30:
                    print(f"❌ {symbol} skipped (not enough data)")
                    continue

                # ensure numeric
                df["close"] = pd.to_numeric(df["close"], errors="coerce")
                df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

                df = df.dropna()

                print(f"🔎 {symbol} → rows: {len(df)}")

                stocks[symbol] = df

            except Exception as e:
                print(f"❌ Error loading {symbol}: {e}")

    print(f"\n✅ Loaded stocks: {len(stocks)}")
    return stocks


# ==============================
# ANALYZE
# ==============================
def analyze_stocks(stocks):
    results = []

    for symbol, df in stocks.items():

        try:
            df = apply_indicators(df)

            score = score_stock(df)

            last_price = df["close"].iloc[-1]

            results.append({
                "symbol": symbol,
                "score": score,
                "price": last_price
            })

        except Exception as e:
            print(f"❌ {symbol} analysis error: {e}")

    return results


# ==============================
# PRINT RESULT
# ==============================
def print_summary(results):
    if not results:
        print("❌ No results")
        return

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    print("\n🔥 TOP STOCKS 🔥\n")

    for r in results[:20]:
        print(f"{r['symbol']} | Score: {r['score']} | Price: {round(r['price'],2)}")

    print(f"\n📊 Total analyzed: {len(results)}")


# ==============================
# RUN
# ==============================
def run():
    stocks = load_stock_data()

    if not stocks:
        print("❌ No valid stock data found")
        return

    results = analyze_stocks(stocks)

    print_summary(results)


if __name__ == "__main__":
    run()
=======
import os
import json

from data_scraper import get_dse_data, get_price_history
from database import save_daily_data
from indicators import calculate_indicators
from scoring_engine import StockInput, score_batch
from prediction_engine import generate_predictions
from high_impact import detect_high_impact
from ai_explainer import generate_explanation


# ==========================================
# SAFE FUNCTION
# ==========================================
def safe_value(val, default=0):
    try:
        return float(val)
    except:
        return default


# ==========================================
# SAVE OUTPUT
# ==========================================
def save_output(results):
    os.makedirs("../output", exist_ok=True)

    bullish_pred, bearish_pred = generate_predictions(results)

    data = {
        "top_bullish": bullish_pred,
        "top_bearish": bearish_pred,
        "high_impact": [],
        "all_stocks": []
    }

    for r in results:
        # Full stock data
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

        # High impact
        impact_score, reasons = detect_high_impact(r)

        if impact_score >= 2:
            data["high_impact"].append({
                "symbol": r.symbol,
                "impact_score": impact_score,
                "reasons": reasons,
                "explanation": generate_explanation(r)
            })

    # Sort high impact
    data["high_impact"] = sorted(
        data["high_impact"],
        key=lambda x: x["impact_score"],
        reverse=True
    )[:20]

    # Save file
    with open("../output/daily-report.json", "w") as f:
        json.dump(data, f, indent=2)

    print("🚀 JSON saved successfully")


# ==========================================
# MAIN
# ==========================================
def main():
    print("🚀 Starting system...\n")

    # Fetch live data
    raw_data = get_dse_data()

    if not raw_data:
        print("❌ No data fetched")
        return

    # Save daily data to database
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

            # Get historical prices
            prices = get_price_history(symbol)

            # Calculate indicators
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

    print("\n⚙️ Scoring stocks...\n")

    results = score_batch(stocks)

    save_output(results)


# ==========================================
# RUN
# ==========================================
if __name__ == "__main__":
    main()
>>>>>>> ba7e25db86fb7ea4f7076427091104d359f89ae4
