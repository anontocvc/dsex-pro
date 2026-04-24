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