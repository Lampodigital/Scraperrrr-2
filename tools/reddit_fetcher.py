import requests
import json
import uuid
from datetime import datetime, timezone

def test_reddit_json():
    # Reddit's .json endpoint often works with a proper user-agent
    url = "https://www.reddit.com/r/ArtificialInteligence/new.json?limit=10"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    print(f"Testing Reddit JSON endpoint: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            articles = []
            posts = data.get("data", {}).get("children", [])
            
            for post in posts:
                p_data = post.get("data", {})
                # Filter for last 24 hours (86400 seconds)
                created_utc = p_data.get("created_utc")
                # if datetime.now(timezone.utc).timestamp() - created_utc > 86400:
                #     continue
                
                # Improvement: Get higher quality preview image if available
                thumbnail = p_data.get("thumbnail")
                preview_images = p_data.get("preview", {}).get("images", [])
                if preview_images:
                    thumbnail = preview_images[0].get("source", {}).get("url", thumbnail)
                
                # Reddit JSON URLs often have &amp; that need clearing
                if thumbnail:
                    thumbnail = thumbnail.replace("&amp;", "&")

                article = {
                    "id": str(uuid.uuid4()),
                    "title": p_data.get("title"),
                    "source": "Reddit",
                    "url": f"https://www.reddit.com{p_data.get('permalink')}",
                    "summary": p_data.get("selftext")[:200] if p_data.get("selftext") else None,
                    "published_at": datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat(),
                    "thumbnail": thumbnail if thumbnail and thumbnail.startswith("http") else None,
                    "tags": ["Reddit", p_data.get("subreddit")],
                    "is_saved": False
                }
                articles.append(article)
            
            if articles:
                print(f"DEBUG: First article thumbnail: {articles[0].get('thumbnail')}")
            print(f"Successfully fetched {len(articles)} recent articles from Reddit.")
            
            # Save to .tmp for aggregator
            with open(".tmp/reddit_latest.json", "w") as f:
                json.dump(articles, f, indent=2)
                
            return articles
        else:
            print(f"Reddit 403/Error: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    return None

if __name__ == "__main__":
    test_reddit_json()
