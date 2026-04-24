import os
import json
import pandas as pd
from datetime import datetime

DATA_DIR = "../data"
HISTORY_DIR = "../data/history"


def get_today_file():
    today = datetime.now().strftime("%Y-%m-%d")
    return f"{DATA_DIR}/{today}.json"


def get_today_data():
    file_path = get_today_file()

    if not os.path.exists(file_path):
        print("❌ No daily data file found")
        return []

    with open(file_path, "r") as f:
        return json.load(f)


# ===================================
# 🔥 CORE: REAL HISTORY BUILDER
# ===================================
def update_history(symbol, stock_data):
    os.makedirs(HISTORY_DIR, exist_ok=True)

    file_path = f"{HISTORY_DIR}/{symbol}.csv"

    new_row = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "close": stock_data["Close"],
        "volume": stock_data["Volume"]
    }

    # =========================
    # IF FILE EXISTS
    # =========================
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)

        # Avoid duplicate date
        if df.iloc[-1]["date"] == new_row["date"]:
            return df

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    else:
        # First time create file
        df = pd.DataFrame([new_row])

    # Keep last 200 days
    df = df.tail(200)

    df.to_csv(file_path, index=False)

    return df