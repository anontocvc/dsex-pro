def generate_predictions(results):
    bullish = []
    bearish = []

    for r in results:

        # ✅ relaxed condition
        if r.signal in ["BUY", "STRONG_BUY"]:
            bullish.append({
                "symbol": r.symbol,
                "score": r.total_score,
                "confidence": r.confidence
            })

        if r.signal in ["SELL", "STRONG_SELL"]:
            bearish.append({
                "symbol": r.symbol,
                "score": r.total_score,
                "confidence": r.confidence
            })

    bullish = sorted(bullish, key=lambda x: x["score"], reverse=True)[:20]
    bearish = sorted(bearish, key=lambda x: x["score"])[:20]

def generate_predictions(results):
    bullish = []
    bearish = []

    for r in results:

        # ✅ relaxed condition
        if r.signal in ["BUY", "STRONG_BUY"]:
            bullish.append({
                "symbol": r.symbol,
                "score": r.total_score,
                "confidence": r.confidence
            })

        if r.signal in ["SELL", "STRONG_SELL"]:
            bearish.append({
                "symbol": r.symbol,
                "score": r.total_score,
                "confidence": r.confidence
            })

    bullish = sorted(bullish, key=lambda x: x["score"], reverse=True)[:20]
    bearish = sorted(bearish, key=lambda x: x["score"])[:20]

    return bullish, bearish
