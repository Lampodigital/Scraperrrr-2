import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright

class BensBitesScraper:
    def __init__(self):
        self.base_url = "https://www.bensbites.com/"
        self.articles = []

    async def get_latest_post_url(self, page):
        """Finds the URL of the most recent newsletter edition."""
        print("Navigating to Ben's Bites homepage...")
        await page.goto(self.base_url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        post_selector = 'div[role="article"] a[href*="/p/"]'
        latest_post = await page.query_selector(post_selector)
        
        if latest_post:
            url = await latest_post.get_attribute("href")
            if url.startswith("/"):
                url = f"{self.base_url}{url}"
            print(f"Latest post found: {url}")
            return url
        return None

    async def scrape_post(self, page, post_url):
        """Scrapes articles from a specific post URL."""
        print(f"Scraping post: {post_url}...")
        await page.goto(post_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        time_tag = await page.query_selector("time")
        if time_tag:
            datetime_str = await time_tag.get_attribute("datetime")
            pub_date = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        else:
            pub_date = datetime.now(timezone.utc)

        # Extraction logic in a single evaluate call
        articles_data = await page.evaluate('''(pubDate) => {
            const results = [];
            const items = Array.from(document.querySelectorAll('li'));
            items.forEach(item => {
                const linkTag = item.querySelector('a');
                if (!linkTag) return;
                
                const url = linkTag.href;
                if (!url || !url.startsWith('http') || url.includes('twitter.com') || url.includes('linkedin.com')) return;
                
                const fullText = item.innerText.trim();
                const title = linkTag.innerText.trim() || fullText.split('\\n')[0];
                const summary = fullText.replace(title, "").replace(/^[\\s\\-\\:\\.]+/g, "").trim();
                
                let thumbnail = null;
                const img = item.querySelector('img');
                if (img && img.src.startsWith('http') && !img.src.includes('profile_picture') && !img.src.includes('author') && !img.src.includes('avatar')) {
                    thumbnail = img.src;
                }
                
                if (title.length > 5) {
                    results.push({ title, url, summary, thumbnail });
                }
            });
            return results;
        }''')

        for item in articles_data:
            article = {
                "id": str(uuid.uuid4()),
                "title": item['title'][:100],
                "source": "Ben's Bites",
                "url": item['url'],
                "summary": item['summary'][:300],
                "published_at": pub_date.isoformat(),
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

            # Load Ben's Bites cookies if available
            try:
                with open("/Users/stefanorossi/Documents/Scraperrrr 2/.tmp/cookies_bensbites.json", "r") as f:
                    cookies = json.load(f)
                    await context.add_cookies(cookies)
                print("✅ Ben's Bites session cookies loaded.")
            except Exception as e:
                print(f"⚠️ Could not load cookies: {e}")

            page = await context.new_page()
            
            try:
                url = await self.get_latest_post_url(page)
                if url:
                    await self.scrape_post(page, url)
            finally:
                await browser.close()
                print(f"✅ Scraped {len(self.articles)} articles from Ben's Bites.")
                return self.articles

if __name__ == "__main__":
    scraper = BensBitesScraper()
    asyncio.run(scraper.run())
