<<<<<<< HEAD
import os
import json
from datetime import datetime

DATA_PATH = "../data"


# ==========================================
# SAVE DAILY DATA
# ==========================================
def save_daily_data(stocks):
    os.makedirs(DATA_PATH, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    file_path = f"{DATA_PATH}/{today}.json"

    with open(file_path, "w") as f:
        json.dump(stocks, f, indent=2)

    print(f"💾 Saved daily data: {today}")


# ==========================================
# LOAD HISTORICAL DATA
# ==========================================
def load_history(symbol, days=120):
    if not os.path.exists(DATA_PATH):
        return []

    files = sorted(os.listdir(DATA_PATH))[-days:]

    prices = []

    for file in files:
        try:
            with open(f"{DATA_PATH}/{file}") as f:
                data = json.load(f)

            for stock in data:
                if stock["symbol"] == symbol:
                    prices.append(stock["close"])
        except:
            continue

=======
import os
import json
from datetime import datetime

DATA_PATH = "../data"


# ==========================================
# SAVE DAILY DATA
# ==========================================
def save_daily_data(stocks):
    os.makedirs(DATA_PATH, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    file_path = f"{DATA_PATH}/{today}.json"

    with open(file_path, "w") as f:
        json.dump(stocks, f, indent=2)

    print(f"💾 Saved daily data: {today}")


# ==========================================
# LOAD HISTORICAL DATA
# ==========================================
def load_history(symbol, days=120):
    if not os.path.exists(DATA_PATH):
        return []

    files = sorted(os.listdir(DATA_PATH))[-days:]

    prices = []

    for file in files:
        try:
            with open(f"{DATA_PATH}/{file}") as f:
                data = json.load(f)

            for stock in data:
                if stock["symbol"] == symbol:
                    prices.append(stock["close"])
        except:
            continue

>>>>>>> ba7e25db86fb7ea4f7076427091104d359f89ae4
    return prices