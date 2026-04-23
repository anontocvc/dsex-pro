import requests
from bs4 import BeautifulSoup
import random
from database import load_history


# ==========================================
# FETCH LIVE DSE DATA
# ==========================================
def get_dse_data():
    url = "https://www.dsebd.org/latest_share_price_scroll_l.php"

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        rows = soup.select("table tr")[1:]

        stocks = []

        for row in rows:
            cols = row.find_all("td")

            if len(cols) < 10:
                continue

            try:
                symbol = cols[1].text.strip()
                close = float(cols[2].text.strip())
                prev_close = float(cols[3].text.strip())
                volume = float(cols[9].text.strip().replace(",", ""))

                stocks.append({
                    "symbol": symbol,
                    "name": symbol,
                    "close": close,
                    "prev_close": prev_close,
                    "volume": volume
                })

            except:
                continue

        print(f"📊 DSE data fetched: {len(stocks)} stocks")
        return stocks

    except Exception as e:
        print("❌ DSE fetch error:", e)
        return get_fallback_data()


# ==========================================
# HISTORICAL DATA FROM DATABASE
# ==========================================
def get_price_history(symbol):
    prices = load_history(symbol)

    # If enough real data exists → use it
    if len(prices) >= 30:
        return prices

    # Otherwise fallback
    return generate_fake_history()


# ==========================================
# FAKE DATA (TEMP)
# ==========================================
def generate_fake_history():
    base = random.uniform(50, 300)
    prices = []

    for _ in range(120):
        change = random.uniform(-2, 2)
        base = max(1, base + change)
        prices.append(base)

    return prices


# ==========================================
# FALLBACK (IF SCRAPER FAILS)
# ==========================================
def get_fallback_data():
    print("⚠️ Using fallback demo data")

    return [
        {"symbol": "GP", "name": "Grameenphone", "close": 310, "prev_close": 305, "volume": 200000},
        {"symbol": "BEXIMCO", "name": "Beximco", "close": 90, "prev_close": 88, "volume": 500000},
        {"symbol": "SQURPHARMA", "name": "Square Pharma", "close": 235, "prev_close": 230, "volume": 300000}
    ]