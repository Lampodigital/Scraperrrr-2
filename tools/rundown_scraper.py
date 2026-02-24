import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright

class RundownScraper:
    def __init__(self):
        self.base_url = "https://www.therundown.ai"
        self.articles = []

    async def get_latest_post_url(self, page):
        print(f"Navigating to {self.base_url}...")
        await page.goto(self.base_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # Refined selector from subagent check
        latest_post = await page.query_selector('a.embla__slide__number, a[href^="/p/"]')
        
        if latest_post:
            url = await latest_post.get_attribute("href")
            if url.startswith("/"):
                url = f"{self.base_url}{url}"
            print(f"Latest Rundown post found: {url}")
            return url
        return None

    async def scrape_post(self, page, post_url):
        print(f"Scraping post: {post_url}...")
        await page.goto(post_url, wait_until="domcontentloaded")
        await asyncio.sleep(4)
        
        # Bypassing the subscription modal
        not_now_button = await page.query_selector('button:has-text("Not now")')
        if not_now_button:
            try:
                await not_now_button.scroll_into_view_if_needed()
                await not_now_button.click(force=True, timeout=5000)
            except:
                print("Could not click 'Not now', proceeding anyway...")
            await asyncio.sleep(1)

        # Extraction logic in a single evaluate call for efficiency
        articles_data = await page.evaluate('''(postUrl) => {
            const results = [];
            
            // 1. Capture Main Articles (Headers + Siblings)
            const headers = Array.from(document.querySelectorAll('h1, h2, h3'));
            headers.forEach(header => {
                const title = header.innerText.trim();
                if (title.length < 10 || title === 'The Rundown' || title.includes('Keep Reading')) return;

                let summary = "";
                let thumbnail = null;
                let url = postUrl;

                let next = header.nextElementSibling;
                let count = 0;
                while (next && count < 10) {
                    if (!thumbnail) {
                        const img = next.querySelector('img');
                        if (img && img.src.startsWith('http') && !img.src.includes('profile_picture') && !img.src.includes('author') && !img.src.includes('avatar')) {
                            thumbnail = img.src;
                        }
                    }
                    if (next.tagName === 'P' && !summary) {
                        summary = next.innerText.trim();
                    }
                    if (!url || url === postUrl) {
                        const link = next.querySelector('a');
                        if (link && link.href.startsWith('http')) url = link.href;
                    }
                    if (['H1', 'H2', 'H3'].includes(next.tagName)) break;
                    next = next.nextElementSibling;
                    count++;
                }
                
                if (title && (summary || thumbnail)) {
                    results.push({ title, url, summary, thumbnail, type: 'article' });
                }
            });

            // 2. Capture Bullet Points (Lists)
            const listItems = Array.from(document.querySelectorAll('li'));
            listItems.forEach(li => {
                const text = li.innerText.trim();
                if (text.length < 30) return;
                
                const link = li.querySelector('a');
                if (!link) return;
                
                const url = link.href;
                const parts = text.split(':');
                let title, summary;
                
                if (parts.length > 1 && parts[0].length < 50) {
                    title = parts[0].trim();
                    summary = parts.slice(1).join(':').trim();
                } else {
                    title = text.substring(0, 80) + '...';
                    summary = text;
                }
                
                results.push({ title, url, summary, thumbnail: null, type: 'bullet' });
            });

            return results;
        }''', post_url)

        for item in articles_data:
            article = {
                "id": str(uuid.uuid4()),
                "title": item['title'],
                "source": "The Rundown AI",
                "url": item['url'],
                "summary": item['summary'][:400],
                "published_at": datetime.now(timezone.utc).isoformat(),
                "thumbnail": item['thumbnail'],
                "tags": ["AI"],
                "is_saved": False
            }
            self.articles.append(article)

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            # Load Rundown cookies if available
            try:
                with open("/Users/stefanorossi/Documents/Scraperrrr 2/.tmp/cookies_rundown.json", "r") as f:
                    cookies = json.load(f)
                    await context.add_cookies(cookies)
                print("✅ Rundown session cookies loaded.")
            except Exception as e:
                print(f"⚠️ Could not load cookies: {e}")

            page = await context.new_page()
            try:
                latest_url = await self.get_latest_post_url(page)
                if latest_url:
                    await self.scrape_post(page, latest_url)
                print(json.dumps(self.articles, indent=2))
                with open(".tmp/rundown_latest.json", "w") as f:
                    json.dump(self.articles, f, indent=2)
            except Exception as e:
                print(f"Scraper error: {e}")
            finally:
                await browser.close()

if __name__ == "__main__":
    scraper = RundownScraper()
    asyncio.run(scraper.run())
