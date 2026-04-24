import os
import sys

print("🚀 STARTING FULL STOCK SYSTEM...\n")

# Get current script directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Python executable path
python = sys.executable

# Step 1: Fetch LIVE DSE data
print("📡 Step 1: Fetching LIVE market data...")
os.system(f'"{python}" "{BASE_DIR}/dse_live_fetcher.py"')

# Step 2: Fetch HISTORY
print("\n📊 Step 2: Fetching HISTORY data...")
os.system(f'"{python}" "{BASE_DIR}/dse_history_fetcher.py"')

# Step 3: Run ANALYSIS
print("\n🧠 Step 3: Running analysis...")
os.system(f'"{python}" "{BASE_DIR}/main.py"')

print("\n✅ ALL DONE (AUTO RUN COMPLETE)")
