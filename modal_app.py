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

# Image setup with Playwright
image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install("requests", "beautifulsoup4", "playwright", "fastapi[standard]")
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
            
            if video_id:
                return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    except: pass
    return None

def get_og_image(url):
    """Fetch Open Graph image for a URL, filtering out common generic icons/logos."""
    try:
        if not url or not url.startswith('http'):
            return None
            
        # 1. Specialized YouTube Handler
        yt_thumb = get_youtube_thumbnail(url)
        if yt_thumb: return yt_thumb

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        candidates = []
        
        # 1. Open Graph & Twitter
        for tag in soup.find_all("meta"):
            prop = tag.get("property", "").lower()
            name = tag.get("name", "").lower()
            content = tag.get("content", "")
            if not content: continue
            
            if prop in ["og:image", "og:image:url", "og:image:secure_url"]:
                candidates.append((10, content))
            elif name in ["twitter:image", "twitter:image:src"]:
                candidates.append((8, content))

        # 2. JSON-LD
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                js = json.loads(s.string)
                def find_img(obj):
                    if isinstance(obj, dict):
                        img = obj.get("image")
                        if isinstance(img, str): return img
                        if isinstance(img, dict): return img.get("url")
                        for v in obj.values():
                            res = find_img(v)
                            if res: return res
                    elif isinstance(obj, list):
                        for v in obj:
                            res = find_img(v)
                            if res: return res
                    return None
                img = find_img(js)
                if img: candidates.append((9, img))
            except: continue

        if not candidates:
            # 3. Fallback to first large image in body (usually avoids headers if we skip the top)
            for img in soup.find_all("img"):
                src = img.get("src")
                if not src or not src.startswith("http"): continue
                alt = img.get("alt", "").lower()
                # Skip things that look like logos
                if any(x in src.lower() or x in alt for x in ["logo", "icon", "banner", "header"]):
                    continue
                candidates.append((5, src))
                break

        if not candidates: return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        block_list = ['logo', 'icon', 'favicon', 'avatar', 'profile', 'header', 'placeholder', 'default', 'newsletter', 'subscribe', 'banner', 'button', 'badge', 'spacer', 'pixel']
        
        for priority, img_url in candidates:
            if not img_url or not img_url.startswith('http'): continue
            url_lower = img_url.lower()
            
            # If it's a high priority (OG) image, we only block it if it's EXPLICITLY a logo file
            # Most sites use /static/logo.png or something similar
            if priority >= 8:
                if any(x in url_lower and "logo" in url_lower for x in [".png", ".jpg", ".svg", ".webp"]):
                    if "article" not in url_lower and "post" not in url_lower:
                        continue
                return img_url
            
            if not any(word in url_lower for word in block_list):
                return img_url
                
        # Last resort: if we have any candidate at all and we're about to return None
        if candidates: return candidates[0][1]
            
    except Exception as e:
        print(f"Error fetching OG image for {url}: {e}")
    return None

def enrich_article(article):
    """Enriches an article with a thumbnail if missing or generic."""
    current_thumb = article.get('thumbnail')
    url = article.get('url')
    if not url: return article

    # Generic logo lists
    generic_fragments = ['substack.com/image/fetch', 'bensbites.com/logo', 'therundown.ai/logo', 'reddit.com/static', 'redditstatic.com']
    is_generic = current_thumb and any(f in current_thumb for f in generic_fragments)
    
    if not current_thumb or is_generic:
        # Don't re-scrape Twitter/X (Requests usually fails, and they often don't have OG images for single tweets)
        if "twitter.com" in url or "x.com" in url:
            return article
            
        new_img = get_og_image(url)
        if new_img:
            article['thumbnail'] = new_img
        elif is_generic:
            article['thumbnail'] = None
                
    return article

def is_real_article(article):
    if not article: return False
    title_lower = (article.get('title') or '').lower()
    block_words = ['rsvp', 'workshop', 'webinar', 'sponsor', 'partner', 'ad ', 'advertisement', 'newsletter', 'subscribe', 'join us', 'referral', 'sign up', 'read more', 'keep reading', 'previous edition', 'archives', 'feedback', 'survey', 'community highlights', 'job board', 'careers', 'hiring']
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
        post_elements = await page.query_selector_all('div[role="article"] a[href*="/p/"]')
        post_urls = []
        for el in post_elements[:2]:
            href = await el.get_attribute("href")
            if href:
                if href.startswith("/"): href = f"https://www.bensbites.com{href}"
                post_urls.append(href)
        
        post_urls = list(dict.fromkeys(post_urls))
        for url in post_urls:
            print(f"   Scraping edition: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            articles_data = await page.evaluate('''() => {
                const results = [];
                // Ben's Bites content is often in <li> or <div> tags
                const items = Array.from(document.querySelectorAll('li, div.post-content > div, div.body > div'));
                
                items.forEach(item => {
                    const link = item.querySelector('a');
                    if (!link) return;
                    const url = link.href;
                    if (!url || !url.startsWith('http') || url.includes('bensbites.com')) return;
                    
                    const title = link.innerText.trim();
                    if (title.length < 10) return;
                    
                    const fullText = item.innerText.trim();
                    const summary = fullText.replace(title, "").trim();
                    
                    // Local image check
                    let thumbnail = null;
                    const img = item.querySelector('img');
                    if (img && img.src.startsWith('http') && !img.src.includes('avatar') && !img.src.includes('profile')) {
                        thumbnail = img.src;
                    }
                    
                    results.push({ title, url, summary, thumbnail });
                });
                return results;
            }''')
            
            for item in articles_data:
                articles.append({
                    "id": str(uuid.uuid4()),
                    "title": item['title'],
                    "source": "Ben's Bites",
                    "url": item['url'],
                    "summary": (item['summary'] or "")[:300],
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
                const headers = Array.from(document.querySelectorAll('h1, h2, h3'));
                headers.forEach(header => {
                    const title = header.innerText.trim();
                    if (title.length < 12 || title.includes("The Rundown")) return;
                    
                    let next = header.nextElementSibling;
                    let summary = "";
                    let url = null;
                    let thumbnail = null;
                    let count = 0;
                    while (next && count < 6) {
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
                    "summary": (item['summary'] or "")[:400],
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
                thumb = p.get("thumbnail")
                if thumb and (not thumb.startswith("http") or any(x in thumb for x in ["redditstatic", "self", "default"])):
                    thumb = None
                articles.append({
                    "id": str(uuid.uuid4()), "title": p.get("title"), "source": "Reddit", "url": f"https://www.reddit.com{p.get('permalink')}", "summary": p.get("selftext")[:200] if p.get("selftext") else None, "published_at": datetime.fromtimestamp(p.get("created_utc"), tz=timezone.utc).isoformat(), "thumbnail": thumb, "tags": ["Reddit"], "is_saved": False
                })
    except Exception as e: print(f"   ⚠️ Reddit error: {e}")
    return articles

# --- MAIN RUNNER ---

@app.function(image=image, volumes={"/data": vol}, timeout=1200)
async def run_scrapers():
    from playwright.async_api import async_playwright
    all_articles = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        for cookie_file in ["cookies_bensbites.json", "cookies_rundown.json"]:
            path = f"/data/{cookie_file}"; 
            if os.path.exists(path):
                with open(path, "r") as f: await context.add_cookies(json.load(f))
        results = await asyncio.gather(scrape_bensbites(context), scrape_rundown(context))
        for r in results: all_articles.extend(r)
        await browser.close()
    all_articles.extend(fetch_reddit())
    filtered = [a for a in all_articles if is_real_article(a)]
    seen_urls = set(); unique_filtered = []
    for a in filtered:
        url = a.get('url')
        if url not in seen_urls: unique_filtered.append(a); seen_urls.add(url)
    print(f"🧹 After filtering and deduplication: {len(unique_filtered)}")
    print("🖼️  Enriching with OG images (Parallel)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        enriched = list(executor.map(enrich_article, unique_filtered))
    final_articles = [a for a in enriched if a.get('title') and len(a['title']) > 5]
    payload = {"last_updated": datetime.now(timezone.utc).isoformat(), "articles": final_articles}
    with open("/data/master_payload.json", "w") as f: json.dump(payload, f, indent=2)
    vol.commit(); print(f"✨ Success! Total unique articles: {len(final_articles)}")
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
    except: return {"error": "No data found. Wait for the first scrape."}

if __name__ == "__main__":
    modal.runner.deploy_app(app)
