import os
import json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")


def load_daily_file():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]

    if not files:
        print("❌ No daily files found")
        return None

    latest = sorted(files)[-1]
    path = os.path.join(DATA_DIR, latest)

    print(f"📂 Loading: {latest}")

    with open(path, "r") as f:
        data = json.load(f)

    return pd.DataFrame(data)


def update_history():
    df = load_daily_file()

    if df is None:
        return

    os.makedirs(HISTORY_DIR, exist_ok=True)

    total = 0

    for _, row in df.iterrows():
        symbol = row["symbol"]
        file_path = os.path.join(HISTORY_DIR, f"{symbol}.csv")

        new_row = pd.DataFrame([row])

        if os.path.exists(file_path):
            old = pd.read_csv(file_path)
            combined = pd.concat([old, new_row], ignore_index=True)
            combined.drop_duplicates(subset=["date"], inplace=True)
        else:
            combined = new_row

        combined.to_csv(file_path, index=False)
        total += 1

    print(f"✅ Updated history for {total} stocks")


def run():
    print("📊 Building history...")
    update_history()


if __name__ == "__main__":
    run()
