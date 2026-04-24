import os

# 🔥 FIX MEMORY (VERY IMPORTANT)
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import gc
from datetime import datetime

# CONFIG
BASE_URL = "https://www.dsebd.org/day_end_archive.php"
DATA_PATH = "data/history"

os.makedirs(DATA_PATH, exist_ok=True)

START_DATE = "01-05-2025"
END_DATE = datetime.today().strftime("%d-%m-%Y")


# FETCH FUNCTION
def fetch_history(symbol):
    print(f"\n📊 Fetching {symbol}...")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    def request_data(start, end):
        payload = {
            "startDate": start,
            "endDate": end,
            "inst": symbol,
            "archive": "data"
        }

        try:
            res = requests.post(BASE_URL, data=payload, headers=headers, timeout=15)

            if res.status_code != 200:
                return None

            soup = BeautifulSoup(res.text, "lxml")
            table = soup.find("table")

            if not table:
                return None

            rows = table.find_all("tr")[1:]

            data = []

            for row in rows:
                cols = row.find_all("td")

                if len(cols) < 7:
                    continue

                try:
                    date = cols[1].text.strip()
                    close = float(cols[5].text.strip())
                    volume = float(cols[6].text.strip().replace(",", ""))

                    data.append({
                        "date": date,
                        "close": close,
                        "volume": volume
                    })
                except:
                    continue

            return data

        except Exception:
            return None

    # TRY 1 (MAIN RANGE)
    data = request_data(START_DATE, END_DATE)

    # TRY 2 (FALLBACK RANGE)
    if not data or len(data) < 20:
        print(f"🔁 Retrying {symbol} with extended range...")
        data = request_data("01-01-2024", END_DATE)

    # FINAL CHECK
    if not data or len(data) < 20:
        print(f"⚠️ Skipped {symbol} (no usable data)")
        return None

    df = pd.DataFrame(data)

    # oldest → newest
    df = df.iloc[::-1].reset_index(drop=True)

    return df


# MAIN RUN
def run():
    stock_file = "data/stock_list.txt"

    if not os.path.exists(stock_file):
        print("❌ stock_list.txt not found")
        return

    with open(stock_file) as f:
        symbols = [s.strip() for s in f.readlines() if s.strip()]

    # 🔥 SAFE TEST MODE (REMOVE LATER)
    symbols = symbols[:50]

    success = 0

    for symbol in symbols:
        df = fetch_history(symbol)

        if df is not None:
            path = os.path.join(DATA_PATH, f"{symbol}.csv")
            df.to_csv(path, index=False)
            success += 1
            print(f"✅ Saved {symbol}")
        else:
            print(f"❌ Failed {symbol}")

        # 🔥 MEMORY CLEANUP
        del df
        gc.collect()

        time.sleep(1)

    print(f"\n🎯 Done. Saved {success} stocks")


# ENTRY
if __name__ == "__main__":
    run()
