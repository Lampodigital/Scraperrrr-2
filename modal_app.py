import modal
import json
import os
import uuid
import asyncio
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
import concurrent.futures

# Configuration
app = modal.App("glaido-scraper")
vol = modal.Volume.from_name("glaido-data", create_if_missing=True)

# Image setup with Playwright
image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install("requests", "beautifulsoup4", "playwright", "fastapi[standard]")
    .run_commands("playwright install chromium")
    .run_commands("playwright install-deps chromium")
)

# --- UTILS ---

def get_og_image(url):
    """Fetch Open Graph image for a URL, filtering out common generic icons/logos."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Priority candidates for article images
            candidates = []
            
            # 1. Standard OG tags
            for attr, name in [("property", "og:image"), ("name", "twitter:image"), ("property", "og:image:url")]:
                tag = soup.find("meta", {attr: name})
                if tag and tag.get("content"):
                    candidates.append(tag["content"])
            
            # 2. Schema.org ImageObject
            import re
            schema_tags = soup.find_all("script", type="application/ld+json")
            for s in schema_tags:
                try:
                    js = json.loads(s.string)
                    # Check for image in common schema structures
                    if isinstance(js, dict):
                        img = js.get("image")
                        if isinstance(img, str): candidates.append(img)
                        elif isinstance(img, dict): candidates.append(img.get("url"))
                except: continue

            # Filter candidates to avoid generic logos/icons
            block_list = ['logo', 'icon', 'avatar', 'profile', 'header', 'placeholder', 'default', 'newsletter-cta', 'subscribe']
            
            for img_url in candidates:
                if not img_url or not img_url.startswith('http'): continue
                
                # Check if it looks like a generic asset
                url_lower = img_url.lower()
                if any(word in url_lower for word in block_list):
                    continue
                
                # If we passed filters, return the first good one
                return img_url
                
            # If no good candidate passed filters, try the first one anyway if we have one
            if candidates:
                return candidates[0]
                
    except Exception as e:
        print(f"Error fetching OG image for {url}: {e}")
    return None

def enrich_article(article):
    """Enriches an article with a thumbnail if missing and ensures generic images are replaced."""
    current_thumb = article.get('thumbnail')
    
    # List of generic image fragments to avoid
    generic_fragments = ['substack.com/image/fetch', 'bensbites.com/logo', 'therundown.ai/logo']
    
    needs_new_image = not current_thumb or any(f in current_thumb for f in generic_fragments)
    
    if needs_new_image and article.get('url'):
        new_img = get_og_image(article['url'])
        if new_img:
            article['thumbnail'] = new_img
            
    return article

def is_real_article(article):
    if not article: return False
    title_lower = (article.get('title') or '').lower()
    block_words = ['rsvp', 'workshop', 'webinar', 'sponsor', 'partner', 'ad ', 'advertisement', 'newsletter', 'subscribe', 'join us', 'referral', 'sign up']
    if any(word in title_lower for word in block_words): return False
    if len(title_lower) < 15 and article.get('source') != "Reddit": return False
    return True

# --- SCRAPER FUNCTIONS ---

async def scrape_bensbites(context):
    print("🤖 Scraping Ben's Bites...")
    page = await context.new_page()
    articles = []
    try:
        await page.goto("https://www.bensbites.com/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        latest_post = await page.query_selector('div[role="article"] a[href*="/p/"]')
        if latest_post:
            url = await latest_post.get_attribute("href")
            if url.startswith("/"): url = f"https://www.bensbites.com{url}"
            print(f"   Found latest post: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            articles_data = await page.evaluate('''() => {
                const results = [];
                // Look for both list items and div-wrapped blocks
                const items = Array.from(document.querySelectorAll('li, div.post-content > div'));
                items.forEach(item => {
                    const link = item.querySelector('a');
                    if (!link) return;
                    const url = link.href;
                    if (!url || typeof url !== 'string' || !url.startsWith('http') || url.includes('twitter.com') || url.includes('linkedin.com')) return;
                    
                    const fullText = item.innerText.trim();
                    const title = link.innerText.trim() || fullText.split('\\n')[0];
                    if (title.length < 5) return;

                    // Try to find an image specific to this item
                    let thumbnail = null;
                    const img = item.querySelector('img');
                    if (img && img.src.startsWith('http') && !img.src.includes('profile') && !img.src.includes('avatar')) {
                        thumbnail = img.src;
                    }
                    
                    results.push({ title, url, summary: fullText.replace(title, "").trim(), thumbnail });
                });
                return results;
            }''')
            
            for item in articles_data:
                articles.append({
                    "id": str(uuid.uuid4()),
                    "title": item['title'],
                    "source": "Ben's Bites",
                    "url": item['url'],
                    "summary": item['summary'][:300],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "thumbnail": item['thumbnail'],
                    "tags": ["AI"],
                    "is_saved": False
                })
    except Exception as e:
        print(f"   ⚠️ Ben's Bites error: {e}")
    return articles

async def scrape_rundown(context):
    print("🤖 Scraping Rundown AI...")
    page = await context.new_page()
    articles = []
    try:
        await page.goto("https://www.therundown.ai", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        latest_post = await page.query_selector('a.embla__slide__number, a[href^="/p/"]')
        if latest_post:
            url = await latest_post.get_attribute("href")
            if url.startswith("/"): url = f"https://www.therundown.ai{url}"
            print(f"   Found latest post: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            try:
                btn = await page.query_selector('button:has-text("Not now")')
                if btn: await btn.click()
            except: pass

            articles_data = await page.evaluate('''() => {
                const results = [];
                // More precise selection for headings that represent articles
                const headers = Array.from(document.querySelectorAll('h1, h2, h3'));
                headers.forEach(header => {
                    const title = header.innerText.trim();
                    if (title.length < 12 || title.includes("The Rundown") || title.includes("Sponsor") || title.includes("Tools")) return;
                    
                    let next = header.nextElementSibling;
                    let summary = "";
                    let url = null;
                    let thumbnail = null;
                    
                    // Traverse adjacent elements to find image and actual link
                    let count = 0;
                    while (next && count < 5) {
                        if (!url) {
                            const link = next.querySelector('a');
                            if (link && link.href.startsWith('http')) url = link.href;
                        }
                        if (!thumbnail) {
                            const img = next.querySelector('img');
                            if (img && img.src.startsWith('http') && !img.src.includes('logo')) thumbnail = img.src;
                        }
                        if (next.tagName === 'P' && !summary) summary = next.innerText.trim();
                        if (['H1', 'H2', 'H3'].includes(next.tagName)) break;
                        next = next.nextElementSibling;
                        count++;
                    }
                    
                    if (title && (url || summary)) {
                        results.push({ title, url: url || window.location.href, summary, thumbnail });
                    }
                });
                return results;
            }''')
            
            for item in articles_data:
                articles.append({
                    "id": str(uuid.uuid4()),
                    "title": item['title'],
                    "source": "The Rundown AI",
                    "url": item['url'],
                    "summary": item['summary'][:400],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "thumbnail": item['thumbnail'],
                    "tags": ["AI"],
                    "is_saved": False
                })
    except Exception as e:
        print(f"   ⚠️ Rundown error: {e}")
    return articles

def fetch_reddit():
    print("🤖 Fetching Reddit...")
    articles = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get("https://www.reddit.com/r/ArtificialInteligence/new.json?limit=15", headers=headers, timeout=10)
        if res.status_code == 200:
            posts = res.json().get("data", {}).get("children", [])
            for post in posts:
                p = post["data"]
                # Filter out generic reddit icons/placeholders
                thumb = p.get("thumbnail")
                if thumb and (not thumb.startswith("http") or any(x in thumb for x in ["redditstatic", "self", "default"])):
                    thumb = None

                articles.append({
                    "id": str(uuid.uuid4()),
                    "title": p.get("title"),
                    "source": "Reddit",
                    "url": f"https://www.reddit.com{p.get('permalink')}",
                    "summary": p.get("selftext")[:200] if p.get("selftext") else None,
                    "published_at": datetime.fromtimestamp(p.get("created_utc"), tz=timezone.utc).isoformat(),
                    "thumbnail": thumb,
                    "tags": ["Reddit"],
                    "is_saved": False
                })
    except Exception as e:
        print(f"   ⚠️ Reddit error: {e}")
    return articles

# --- MAIN RUNNER ---

@app.function(image=image, volumes={"/data": vol}, timeout=600)
async def run_scrapers():
    from playwright.async_api import async_playwright
    
    all_articles = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        # Load cookies
        for cookie_file in ["cookies_bensbites.json", "cookies_rundown.json"]:
            path = f"/data/{cookie_file}"
            if os.path.exists(path):
                print(f"✅ Loading {cookie_file}")
                with open(path, "r") as f:
                    await context.add_cookies(json.load(f))
        
        # Scrape in parallel (Playwright)
        results = await asyncio.gather(
            scrape_bensbites(context),
            scrape_rundown(context)
        )
        for r in results: all_articles.extend(r)
        
        await browser.close()

    # Reddit (Requests)
    all_articles.extend(fetch_reddit())

    print(f"🧹 Initial count: {len(all_articles)}")
    filtered = [a for a in all_articles if is_real_article(a)]
    
    # Deduplicate by URL to prevent repeating articles
    seen_urls = set()
    unique_filtered = []
    for a in filtered:
        url = a.get('url')
        if url not in seen_urls:
            unique_filtered.append(a)
            seen_urls.add(url)
    
    print(f"🧹 After filtering and deduplication: {len(unique_filtered)}")
    
    print("🖼️  Enriching with OG images (Parallel)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        enriched = list(executor.map(enrich_article, unique_filtered))

    payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "articles": enriched
    }

    with open("/data/master_payload.json", "w") as f:
        json.dump(payload, f, indent=2)
    
    vol.commit()
    print(f"✨ Success! Total unique articles: {len(enriched)}")
    return payload

@app.function(image=image, schedule=modal.Cron("0 0 * * *"), volumes={"/data": vol})
def daily_scrape():
    import asyncio
    asyncio.run(run_scrapers.remote())

@app.function(image=image, volumes={"/data": vol})
@modal.fastapi_endpoint(method="GET")
def get_data():
    try:
        with open("/data/master_payload.json", "r") as f:
            return json.load(f)
    except:
        return {"error": "No data found. Wait for the first scrape."}

if __name__ == "__main__":
    modal.runner.deploy_app(app)
