import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ---------------- DRIVER ---------------- #
def create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    return driver


# ---------------- SCRAPER ---------------- #
def fetch_dse_stock_list():
    driver = create_driver()
    stocks = set()

    try:
        print("🌐 Opening AmarStock homepage...")
        driver.get("https://www.amarstock.com/")
        time.sleep(5)

        print("➡️ Clicking Share Price...")
        driver.find_element(By.LINK_TEXT, "Share Price").click()
        time.sleep(6)

        print("📄 Scraping stocks (SAFE MODE)...")

        # 🔥 retry loop to avoid stale error
        for _ in range(3):
            try:
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

                for i in range(len(rows)):
                    try:
                        cols = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")[i].find_elements(By.TAG_NAME, "td")

                        if len(cols) > 1:
                            symbol = cols[1].text.strip().upper()

                            if symbol:
                                stocks.add(symbol)

                    except:
                        continue

                break

            except:
                print("⚠️ Retry scraping...")
                time.sleep(3)

        print(f"✅ Total stocks found: {len(stocks)}")
        return list(stocks)

    except Exception as e:
        print("❌ ERROR:", str(e))
        return []

    finally:
        try:
            driver.quit()
        except:
            pass


# ---------------- SAVE ---------------- #
def save_stock_list(stocks):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "data", "stock_list.txt")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w") as f:
        for s in sorted(stocks):
            f.write(s + "\n")

    print(f"💾 Saved → {file_path}")


# ---------------- RUN ---------------- #
def run():
    stocks = fetch_dse_stock_list()

    if stocks:
        save_stock_list(stocks)
        print("✅ Stock list saved successfully!")
    else:
        print("❌ No stocks found")


if __name__ == "__main__":
    run()
