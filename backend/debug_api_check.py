# backend/debug_api_check.py
import os
from datetime import date
import requests
import pandas as pd
from dotenv import load_dotenv

# Load .env from project root or backend folder
load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")


def check_newsapi(ticker: str, start: date, end: date):
    print(f"\n=== Checking NewsAPI for {ticker} from {start} to {end} ===")
    if not NEWSAPI_KEY:
        print("ERROR: NEWSAPI_KEY is not set in environment/.env")
        return

    url = "https://newsapi.org/v2/everything"
    query = f'"{ticker}" AND (stock OR share OR market)'

    params = {
        "q": query,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": 50,
        "apiKey": NEWSAPI_KEY,
    }

    resp = requests.get(url, params=params, timeout=10)
    print("Status:", resp.status_code)
    print("URL:", resp.url)

    if resp.status_code != 200:
        print("Body:", resp.text[:500])
        return

    data = resp.json()
    articles = data.get("articles", [])
    print("Total articles:", len(articles))

    if articles:
        df = pd.DataFrame(
            [
                {
                    "published_at": a.get("publishedAt"),
                    "title": a.get("title"),
                    "source": (a.get("source") or {}).get("name"),
                }
                for a in articles
            ]
        )
        print("\nSample articles:")
        print(df.head(5))


def check_twitter(ticker: str):
    print(f"\n=== Checking Twitter for {ticker} (recent search) ===")
    if not TWITTER_BEARER_TOKEN:
        print("WARNING: TWITTER_BEARER_TOKEN is not set – skipping Twitter")
        return

    url = "https://api.twitter.com/2/tweets/search/recent"
    query = f'(${ticker} OR {ticker}) (stock OR shares OR market) lang:en -is:retweet'

    params = {
        "query": query,
        "max_results": 20,
        "tweet.fields": "created_at,text,lang",
    }
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}

    resp = requests.get(url, params=params, headers=headers, timeout=10)
    print("Status:", resp.status_code)
    print("URL:", resp.url)

    if resp.status_code != 200:
        print("Body:", resp.text[:500])
        return

    data = resp.json()
    tweets = data.get("data", [])
    print("Total tweets:", len(tweets))

    if tweets:
        df = pd.DataFrame(
            [
                {
                    "created_at": t.get("created_at"),
                    "text": t.get("text"),
                }
                for t in tweets
            ]
        )
        print("\nSample tweets:")
        print(df.head(5))


if __name__ == "__main__":
    # Choose a ticker and date range you care about
    t = "AAPL"
    start = date(2023, 1, 1)
    end = date(2023, 1, 10)

    check_newsapi(t, start, end)
    check_twitter(t)