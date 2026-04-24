def score_stock(df):
    score = 0

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # =========================
    # TREND (STRONG TREND)
    # =========================
    if last["ema20"] > last["ema50"]:
        score += 2

        # stronger trend
        if last["close"] > last["ema20"]:
            score += 1
    else:
        score -= 2

    # =========================
    # RSI MOMENTUM
    # =========================
    if 55 < last["rsi"] < 70:
        score += 2
    elif last["rsi"] > 70:
        score -= 1
    elif last["rsi"] < 40:
        score -= 2

    # =========================
    # MOMENTUM ACCELERATION
    # =========================
    if last["close"] > prev["close"]:
        score += 1

    # =========================
    # BREAKOUT (NEW HIGH)
    # =========================
    if last["close"] >= df["close"].rolling(20).max().iloc[-1]:
        score += 2

    # =========================
    # VOLUME EXPLOSION
    # =========================
    if last["volume"] > (1.5 * last["vol_ma20"]):
        score += 2
    elif last["volume"] > last["vol_ma20"]:
        score += 1

    # =========================
    # WEAK STOCK PENALTY
    # =========================
    if last["close"] < last["ema50"]:
        score -= 2

    return score