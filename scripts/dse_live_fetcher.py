import requests
import pandas as pd
from bs4 import BeautifulSoup
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

URL = "https://www.dsebd.org/latest_share_price_scroll_l.php"


def fetch_dse_data():
    print("🌐 Scraping REAL DSE data...")

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(URL, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "lxml")

        table = soup.find(
            "table",
            {"class": "table table-bordered background-white shares-table fixedHeader"}
        )

        if table is None:
            print("❌ Table not found")
            return None

        rows = table.find_all("tr")[1:]

        data = []

        for row in rows:
            cols = row.find_all("td")

            if len(cols) < 11:
                continue

            try:
                symbol = cols[1].text.strip()
                close = float(cols[2].text.strip())
                volume = float(cols[10].text.strip().replace(",", ""))

                data.append({
                    "symbol": symbol,
                    "close": close,
                    "volume": volume
                })

            except:
                continue

        df = pd.DataFrame(data)

        if df.empty:
            print("❌ No data parsed")
            return None

        # ✅ STEP 1: DATA CLEANING

        print(f"📊 Raw scraped: {len(df)} stocks")

        # remove invalid values
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

        df.dropna(inplace=True)

        # remove zero / bad values
        df = df[(df["close"] > 0) & (df["volume"] > 0)]

        # remove duplicates
        df.drop_duplicates(subset=["symbol"], inplace=True)

        df.reset_index(drop=True, inplace=True)

        print(f"🧹 Cleaned data: {len(df)} stocks")

        # add date
        df["date"] = datetime.today().strftime("%Y-%m-%d")

        return df

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def save_daily_data(df):
    os.makedirs(DATA_DIR, exist_ok=True)

    today = datetime.today().strftime("%Y-%m-%d")
    path = os.path.join(DATA_DIR, f"{today}.json")

    df.to_json(path, orient="records", indent=2)

    print(f"💾 Saved → {path}")


def run():
    df = fetch_dse_data()

    if df is not None:
        save_daily_data(df)
    else:
        print("❌ No data fetched")


if __name__ == "__main__":
    run()
