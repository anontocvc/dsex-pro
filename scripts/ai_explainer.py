def generate_explanation(stock):
    """
    Generate human-readable explanation for a stock
    """

    reasons = []

    # Trend
    if stock.total_score >= 7:
        reasons.append("strong bullish momentum")
    elif stock.total_score <= 4:
        reasons.append("bearish pressure")
    else:
        reasons.append("sideways/neutral trend")

    # RSI
    if stock.breakdown.rsi_score >= 7:
        reasons.append("healthy RSI strength")
    elif stock.breakdown.rsi_score <= 4:
        reasons.append("weak RSI signal")

    # Volume
    if stock.volume_ratio > 1.5:
        reasons.append("unusual high trading volume")

    # News
    if stock.breakdown.news_sentiment >= 7:
        reasons.append("positive news sentiment")
    elif stock.breakdown.news_sentiment <= 4:
        reasons.append("negative news sentiment")

    # Confidence
    if stock.confidence >= 70:
        reasons.append("high confidence setup")

    # Combine
    explanation = ", ".join(reasons)

    return explanation.capitalize()