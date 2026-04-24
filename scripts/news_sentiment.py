import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from cache import load_cache, save_cache


def get_news_sentiment(symbol):
    cached = load_cache(f"news_{symbol}")
    if cached is not None:
        return cached

    try:
        url = f"https://news.google.com/search?q={symbol}+Bangladesh+stock"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")

        texts = []
        for a in soup.find_all("a")[:10]:
            if len(a.text) > 20:
                texts.append(a.text)

        if not texts:
            save_cache(f"news_{symbol}", 0)
            return 0

        score = sum(TextBlob(t).sentiment.polarity for t in texts) / len(texts)

        save_cache(f"news_{symbol}", score)
        return score

    except:
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from cache import load_cache, save_cache


def get_news_sentiment(symbol):
    cached = load_cache(f"news_{symbol}")
    if cached is not None:
        return cached

    try:
        url = f"https://news.google.com/search?q={symbol}+Bangladesh+stock"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")

        texts = []
        for a in soup.find_all("a")[:10]:
            if len(a.text) > 20:
                texts.append(a.text)

        if not texts:
            save_cache(f"news_{symbol}", 0)
            return 0

        score = sum(TextBlob(t).sentiment.polarity for t in texts) / len(texts)

        save_cache(f"news_{symbol}", score)
        return score

    except:
        return 0
