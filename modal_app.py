import modal
import json
import os
import uuid
import asyncio
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import re
from urllib.parse import urlparse, parse_qs

# Configuration
app = modal.App("glaido-scraper")
vol = modal.Volume.from_name("glaido-data", create_if_missing=True)

# Image setup (Playwright no longer needed for Newsletters, but kept for future niche scrapers/Reddit expansion)
image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install("requests", "beautifulsoup4", "playwright", "fastapi[standard]", "feedparser")
    .run_commands("playwright install chromium")
    .run_commands("playwright install-deps chromium")
)

# --- UTILS ---

def get_youtube_thumbnail(url):
    try:
        if "youtube.com" in url or "youtu.be" in url:
            video_id = None
            if "youtu.be" in url:
                video_id = url.split("/")[-1].split("?")[0]
            else:
                qs = parse_qs(urlparse(url).query)
                video_id = qs.get("v", [None])[0]
            if video_id: return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    except: pass
    return None

def get_og_image(url):
    try:
        if not url or not url.startswith('http') or "twitter.com" in url or "x.com" in url: return None
        yt_thumb = get_youtube_thumbnail(url)
        if yt_thumb: return yt_thumb
        headers = { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, 'html.parser')
        candidates = []
        for tag in soup.find_all("meta"):
            prop = (tag.get("property") or "").lower()
            name = (tag.get("name") or "").lower()
            content = tag.get("content", "")
            if not content: continue
            if prop in ["og:image", "og:image:url"]: candidates.append((10, content))
            elif name in ["twitter:image", "twitter:image:src"]: candidates.append((8, content))
        if not candidates: return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    except: return None

def enrich_article(article):
    """Enriches an individual story with a thumbnail if missing or generic."""
    current_thumb = article.get('thumbnail')
    url = article.get('url')
    if not url: return article
    generic_fragments = ['substack.com/image/fetch', 'bensbites.com/logo', 'therundown.ai/logo', 'redditfast', 'reddit.com/static', 'redditstatic.com']
    is_generic = current_thumb and any(f in current_thumb for f in generic_fragments)
    if not current_thumb or is_generic:
        new_img = get_og_image(url)
        if new_img: article['thumbnail'] = new_img
        elif is_generic: article['thumbnail'] = None
    return article

def is_real_article(article):
    """Refined filtering for individual stories."""
    if not article: return False
    title = (article.get('title') or '').strip()
    summary = (article.get('summary') or '').strip()
    
    if len(title) < 15: return False
    # Reject titles that look like sentence fragments (end with comma or are all lowercase)
    if title.endswith(',') or title.endswith(':') or title.endswith(';'): return False
    # Title should read like a headline: starts with uppercase, contains at least 2 words
    words = title.split()
    if len(words) < 3: return False
    # If the title starts lowercase it's likely a fragment of surrounding text
    if title[0].islower(): return False
    # Reject if title has too many lowercase function words as a proportion (likely a sentence fragment)
    # A real headline has ≥ 1 word capitalized beyond the first
    capitalized_count = sum(1 for w in words if w and w[0].isupper())
    if capitalized_count < 1: return False

    title_lower = title.lower()
    ui_phrases = ['see example', 'live example', 'read more', 'click here', 'follow on', 'view on', 'subscribe', 'newsletter', 'sign up', 'unsubscribe']
    if any(p in title_lower for p in ui_phrases): return False

    block_words = ['rsvp', 'workshop', 'webinar', 'sponsor', 'partner', 'ad ', 'advertisement', 'referral', 'free credits', 'get $', 'off deal', 'job board', 'hiring', 'careers', 'legal', 'tos', 'terms', 'archives', 'feedback', 'survey', 'community highlights', 'good morning', 'in today']
    if any(word in title_lower for word in block_words): return False
    
    if article.get('source') != "Reddit" and len(summary) < 40: return False

    return True

# --- NEW RSS-FIRST SCRAPERS ---

def get_edition_resume(soup):
    """Extracts a 2-3 sentence teaser/resume from the first substantial text blocks."""
    paragraphs = []
    # Look for the first few paragraphs that aren't too short or navigational
    for p in soup.find_all(['p', 'div']):
        text = p.get_text().strip()
        # Skip short snippets, ads, or header junk
        if len(text) > 60 and not any(x in text.lower() for x in ['subscribe', 'view in browser', 'read online']):
            # Clean up extra whitespace/newlines
            clean_text = re.sub(r'\s+', ' ', text)
            paragraphs.append(clean_text)
            if len(paragraphs) >= 2: break
    
    resume = " ".join(paragraphs)
    if len(resume) > 350:
        resume = resume[:347] + "..."
    return resume

def scrape_rss_edition(feed_url, source_name):
    """Fetches and parses a newsletter edition from RSS."""
    print(f"🤖 Scraping RSS: {source_name}...")
    import feedparser
    articles = []
    feed = feedparser.parse(feed_url)
    
    # Take the latest 5 editions for broader coverage
    for entry in feed.entries[:5]:
        edition_id = str(uuid.uuid4())
        html_content = entry.get('content', [{}])[0].get('value', entry.get('description', ''))
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. Get Lead Image
        lead_image = None
        # Check enclosures
        for enc in entry.get('enclosures', []):
            if enc.get('type', '').startswith('image/'):
                lead_image = enc.get('href')
                break
        
        # Fallback 1: Feed image
        if not lead_image and hasattr(feed.feed, 'image'):
            lead_image = feed.feed.image.href

        # Fallback 2: First large image in soup (avoid tiny icons)
        if not lead_image:
            for img in soup.find_all('img'):
                src = img.get('src')
                width = img.get('width', '500') # Assume large if no width
                if src and src.startswith('http') and int(re.sub(r'\D', '', str(width)) or 500) > 100:
                    lead_image = src
                    break

        # 2. Extract Edition Resume (Heuristic)
        resume = get_edition_resume(soup) or (entry.summary[:300] if hasattr(entry, 'summary') else "")

        # 3. Extract Nested Stories
        sub_stories = []
        # Newsletters often use h2 or strong links for main stories
        potential_story_containers = soup.find_all(['h2', 'h3', 'strong'])
        
        for container in potential_story_containers:
            link = container.find('a') if hasattr(container, 'find') else None
            # If not in h2/h3, maybe it's just an <a> tag that's prominent
            if not link and container.name == 'a': link = container
            
            if not link: continue
            
            href = link.get('href')
            if not href or not href.startswith('http') or any(x in href.lower() for x in ['bensbites.com', 'therundown.ai', 'substack.com', 'beehiiv.com', 'twitter.com', 'x.com']):
                continue
            
            title = link.get_text().strip()
            if len(title) < 15: continue
            
            # Extract summary by looking at subsequent siblings
            summary_parts = []
            curr = container
            # If it's a strong tag inside a p, move up to p
            if curr.name == 'strong' and curr.parent and curr.parent.name == 'p':
                curr = curr.parent
            
            limit = 0
            sibling = curr.next_sibling
            while sibling and limit < 3:
                txt = sibling.get_text().strip() if hasattr(sibling, 'get_text') else str(sibling).strip()
                if txt and len(txt) > 20:
                    summary_parts.append(txt)
                    if len(txt) > 80: break # Found a good paragraph
                sibling = sibling.next_sibling
                limit += 1

            sub_stories.append({
                "id": str(uuid.uuid4()),
                "title": title,
                "url": href,
                "summary": " ".join(summary_parts)[:400],
                "thumbnail": None # Will be enriched via OG tags later
            })

        # Filter stories to ensure high quality
        valid_stories = [s for s in sub_stories if is_real_article({"title": s['title'], "summary": s['summary'], "source": source_name})]
        
        # Remove duplicates by URL
        seen_urls = set()
        unique_stories = []
        for s in valid_stories:
            if s['url'] not in seen_urls:
                unique_stories.append(s)
                seen_urls.add(s['url'])

        articles.append({
            "id": edition_id,
            "type": "edition",
            "title": entry.title,
            "source": source_name,
            "url": entry.link,
            "resume": resume,
            "summary": resume, # Compatibility fallback
            "published_at": entry.published if hasattr(entry, 'published') else datetime.now(timezone.utc).isoformat(),
            "thumbnail": lead_image,
            "stories": unique_stories[:12] # Keep up to 12; frontend shows 3 by default with Show More
        })
    
    return articles

def fetch_reddit():
    print("🤖 Fetching Reddit...")
    articles = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get("https://www.reddit.com/r/ArtificialInteligence/new.json?limit=10", headers=headers, timeout=10)
        if res.status_code == 200:
            for post in res.json().get("data", {}).get("children", []):
                p = post["data"]
                articles.append({
                    "id": str(uuid.uuid4()),
                    "type": "article",
                    "title": p.get("title"),
                    "source": "Reddit",
                    "url": f"https://www.reddit.com{p.get('permalink')}",
                    "summary": p.get("selftext")[:400] if p.get("selftext") else None,
                    "published_at": datetime.fromtimestamp(p.get("created_utc"), tz=timezone.utc).isoformat(),
                    "thumbnail": p.get("thumbnail") if p.get("thumbnail", "").startswith("http") else None,
                    "stories": [] # Reddit posts are flat
                })
    except Exception as e: print(f"   ⚠️ Reddit Error: {e}")
    return articles

# --- MAIN RUNNER ---

@app.function(image=image, volumes={"/data": vol}, timeout=1200)
async def run_scrapers():
    all_content = []
    
    # Newsletter RSS
    feeds = [
        ("https://www.bensbites.com/feed", "Ben's Bites"),
        ("https://rss.beehiiv.com/feeds/2R3C6Bt5wj.xml", "The Rundown AI")
    ]
    
    for url, name in feeds:
        try:
            all_content.extend(scrape_rss_edition(url, name))
        except Exception as e:
            print(f"   ⚠️ Error scraping {name}: {e}")

    # Reddit
    all_content.extend(fetch_reddit())

    # Enrichment (for nested stories and flat reddit posts)
    print("🖼️  Enriching with OG images...")
    
    def enrich_item(item):
        # Enrich the edition itself if image is generic
        enrich_article(item)
        # Enrich individual stories
        for story in item.get('stories', []):
            enrich_article(story)
        return item

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        final_content = list(executor.map(enrich_item, all_content))

    payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "articles": final_content # Keeping key 'articles' for frontend compatibility but content is now hierarchical
    }
    
    with open("/data/master_payload.json", "w") as f:
        json.dump(payload, f, indent=2)
    
    vol.commit()
    print(f"✨ Success! Total editions/posts: {len(final_content)}")
    return payload

@app.function(image=image, schedule=modal.Cron("0 0 * * *"), volumes={"/data": vol})
def daily_scrape():
    import asyncio
    asyncio.run(run_scrapers.remote())

@app.function(image=image, volumes={"/data": vol})
@modal.fastapi_endpoint(method="GET")
def get_data():
    try:
        vol.reload()
        with open("/data/master_payload.json", "r") as f: return json.load(f)
    except: return {"error": "No data found."}

if __name__ == "__main__":
    modal.runner.deploy_app(app)
