import pandas as pd


def calculate_indicators(prices):
    df = pd.DataFrame(prices, columns=["close"])

    # EMA
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()

    # RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()

    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()

    return {
        "rsi": float(rsi.iloc[-1]),
        "macd": float(macd.iloc[-1]),
        "macd_signal": float(signal.iloc[-1]),
        "ema20": float(df["ema20"].iloc[-1]),   # ✅ EXACT NAME
        "ema50": float(df["ema50"].iloc[-1]),
        "ema200": float(df["ema200"].iloc[-1]),
        "atr": 2,
        "bb_upper": prices[-1] * 1.1,
        "bb_lower": prices[-1] * 0.9
    }