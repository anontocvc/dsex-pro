import json
import os
from datetime import datetime

CACHE_DIR = "../cache"


def _path(name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{name}.json")


def load_cache(name):
    path = _path(name)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return None


def save_cache(name, data):
    path = _path(name)
    with open(path, "w") as f:
        json.dump(data, f)


# ✅ IMPORTANT: THIS FIXES YOUR ERROR
def is_today(timestamp):
    try:
        cache_date = datetime.fromisoformat(timestamp).date()
        return cache_date == datetime.today().date()
    except:
        return False