import asyncio
import json
import os
import concurrent.futures
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

def get_og_image(url):
    """Extract og:image or twitter:image from a URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for attr, name in [("property", "og:image"), ("name", "twitter:image"), ("property", "og:image:url")]:
                tag = soup.find("meta", {attr: name})
                if tag and tag.get("content"):
                    return tag["content"]
    except Exception:
        pass
    return None

def enrich_article(article):
    """Fetch OG image for a single article if missing a thumbnail."""
    if not article.get('thumbnail') and article.get('url'):
        img = get_og_image(article['url'])
        if img:
            article['thumbnail'] = img
    return article

async def run_scraper(script_name):
    print(f"Executing {script_name}...")
    try:
        process = await asyncio.create_subprocess_exec(
            'python3', script_name,
            cwd='/Users/stefanorossi/Documents/Scraperrrr 2'
        )
        await process.wait()
        return True
    except Exception as e:
        print(f"Error running {script_name}: {e}")
        return False

def is_real_article(article):
    """Filter out ads, sponsors, RSVPs, and meta-content."""
    if not article: return False
    
    title_lower = (article.get('title') or '').lower()
    summary_lower = (article.get('summary') or '').lower()
    url_lower = (article.get('url') or '').lower()
    
    # Block list for titles and summaries
    block_words = [
        'rsvp', 'workshop', 'webinar', 'sponsor', 'partner', 'ad ', 'advertisement',
        'read our last', 'stay up to date', 'referral', 'survey', 'poll', 
        'keep reading', 'newsletter', 'subscribe', 'join us', 'bootcamp',
        'roundtable', 'feedback', 'calendar-events', 'authors/', 'guides/'
    ]
    
    for word in block_words:
        if word in title_lower:
            return False
            
    # Specific filtering for Rundown AI tool guide or other non-news
    if "today’s ai tool guide" in title_lower:
        return False
        
    # Minimum length for meaningful content (unless it has a specific layout)
    if len(title_lower) < 15 and article.get('source') != "Reddit":
        return False
        
    return True

async def main():
    print("🚀 Starting Aggregator...")
    
    scrapers = [
        'tools/bensbites_scraper.py',
        'tools/rundown_scraper.py',
        'tools/reddit_fetcher.py'
    ]
    
    await asyncio.gather(*(run_scraper(s) for s in scrapers))
    
    master_articles = []
    
    tmp_files = {
        "Ben's Bites": '.tmp/bensbites_latest.json',
        'The Rundown AI': '.tmp/rundown_latest.json',
        'Reddit': '.tmp/reddit_latest.json'
    }
    
    for source, path in tmp_files.items():
        if os.path.exists(path):
            with open(path, 'r') as f:
                articles = json.load(f)
            
            # 1. Filter out non-articles
            original_count = len(articles)
            articles = [a for a in articles if is_real_article(a)]
            filtered_count = original_count - len(articles)
            if filtered_count > 0:
                print(f"🧹 Filtered out {filtered_count} non-article items from {source}")

            # 2. Enrich remaining articles with OG images
            print(f"🖼️  Enriching {source} articles with OG images (parallel)...")
            articles_needing_images = [a for a in articles if not a.get('thumbnail')]
            print(f"   → {len(articles_needing_images)}/{len(articles)} articles need images")
            
            if articles_needing_images:
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    enriched = list(executor.map(enrich_article, articles_needing_images))
                # Merge back
                enriched_ids = {a['id']: a for a in enriched}
                articles = [enriched_ids.get(a['id'], a) for a in articles]
            
            got_images = sum(1 for a in articles if a.get('thumbnail'))
            print(f"   ✅ {got_images}/{len(articles)} articles now have images from {source}")
            master_articles.extend(articles)
        else:
            print(f"⚠️ Missing data from {source} ({path})")
            
    # Sort by published_at (newest first)
    master_articles.sort(key=lambda x: x['published_at'], reverse=True)
    
    payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "articles": master_articles,
        "saved_ids": []
    }
    
    with open(".tmp/master_payload.json", "w") as f:
        json.dump(payload, f, indent=2)
    
    dashboard_path = "dashboard/public/data.json"
    if os.path.exists("dashboard/public"):
        with open(dashboard_path, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"📡 Synced data to {dashboard_path}")
        
    print(f"\n✨ Aggregation Complete. Total Articles: {len(master_articles)}")

if __name__ == "__main__":
    asyncio.run(main())
