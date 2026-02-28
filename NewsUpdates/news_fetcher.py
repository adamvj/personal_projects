import feedparser
import requests

FEEDS = {
    "Tech": "https://news.google.com/rss/search?q=technology+when:12h&hl=en-US&gl=US&ceid=US:en",
    "AI": "https://news.google.com/rss/search?q=artificial+intelligence+when:12h&hl=en-US&gl=US&ceid=US:en",
    "Trading": "https://news.google.com/rss/search?q=stock+market+when:12h&hl=en-US&gl=US&ceid=US:en",
    "TechCrunch": "https://techcrunch.com/category/startups/feed/",
    "Venture Capital": "https://techcrunch.com/category/venture/feed/",
    "Hacker News": "https://news.ycombinator.com/rss"
}

def fetch_top_news(limit_per_category=3):
    """Fetches top news from predefined RSS feeds and returns a formatted string."""
    news_text = ""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    for category, url in FEEDS.items():
        news_text += f"\n--- {category.upper()} NEWS ---\n"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(response.content)
            for i, entry in enumerate(feed.entries[:limit_per_category]):
                title = entry.title
                news_text += f"{i+1}. {title}\n"
        except Exception as e:
            news_text += f"Error fetching {category} news: {e}\n"
    return news_text.strip()

if __name__ == "__main__":
    print(fetch_top_news())
