import pandas as pd


def apply_indicators(df):
    df = df.copy()

    # =========================
    # BASIC CLEANING
    # =========================
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    df = df.dropna().reset_index(drop=True)

    if len(df) < 50:
        raise ValueError("Not enough data for indicators")

    # =========================
    # EMA (TREND)
    # =========================
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()

    # =========================
    # RSI (MOMENTUM)
    # =========================
    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()

    rs = avg_gain / avg_loss

    df["rsi"] = 100 - (100 / (1 + rs))

    # =========================
    # VOLUME MA
    # =========================
    df["vol_ma20"] = df["volume"].rolling(20).mean()

    # =========================
    # PRICE MOMENTUM
    # =========================
    df["price_change"] = df["close"].pct_change()

    return df