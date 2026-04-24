<<<<<<< HEAD
def detect_high_impact(stock):
    """
    Detect high-impact stocks based on multiple signals
    """

    score = 0
    reasons = []

    # 📊 Volume spike
    if stock.volume_ratio > 1.3:
        score += 2
        reasons.append("Volume spike")

    # 📈 Price movement
    if abs(stock.price_change_pct) > 1:
        score += 2
        reasons.append("Price movement")

    # 📉 / 📈 Strong signal
    if stock.total_score >= 7:
        score += 2
        reasons.append("Strong bullish setup")
    elif stock.total_score <= 4:
        score += 2
        reasons.append("Strong bearish setup")

    # 📰 News sentiment
    if stock.breakdown.news_sentiment >= 6:
        score += 2
        reasons.append("Positive news")
    elif stock.breakdown.news_sentiment <= 4:
        score += 1
        reasons.append("Negative/weak news")

    # 🎯 Confidence
    if stock.confidence >= 65:
        score += 1
        reasons.append("High confidence")

=======
def detect_high_impact(stock):
    """
    Detect high-impact stocks based on multiple signals
    """

    score = 0
    reasons = []

    # 📊 Volume spike
    if stock.volume_ratio > 1.3:
        score += 2
        reasons.append("Volume spike")

    # 📈 Price movement
    if abs(stock.price_change_pct) > 1:
        score += 2
        reasons.append("Price movement")

    # 📉 / 📈 Strong signal
    if stock.total_score >= 7:
        score += 2
        reasons.append("Strong bullish setup")
    elif stock.total_score <= 4:
        score += 2
        reasons.append("Strong bearish setup")

    # 📰 News sentiment
    if stock.breakdown.news_sentiment >= 6:
        score += 2
        reasons.append("Positive news")
    elif stock.breakdown.news_sentiment <= 4:
        score += 1
        reasons.append("Negative/weak news")

    # 🎯 Confidence
    if stock.confidence >= 65:
        score += 1
        reasons.append("High confidence")

>>>>>>> ba7e25db86fb7ea4f7076427091104d359f89ae4
    return score, reasons