import asyncio
import json
from playwright.async_api import async_playwright

async def debug_view():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # Load Ben's Bites cookies
        try:
            with open("/Users/stefanorossi/Documents/Scraperrrr 2/.tmp/cookies_bensbites.json", "r") as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
            print("✅ Ben's Bites session cookies loaded.")
        except Exception as e:
            print(f"⚠️ Could not load cookies: {e}")

        page = await context.new_page()
        url = "https://www.bensbites.com/p/big-upgrade-for-sonnet"
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(5)
        
        # Take screenshot to see if modal is gone and content is visible
        await page.screenshot(path="/Users/stefanorossi/.gemini/antigravity/brain/7add8a75-7426-44f3-80bc-3451ab1e946c/bensbites_authenticated_debug.png", full_page=True)
        
        # Check for images and summaries
        content = await page.evaluate('''() => {
            const results = [];
            const headers = Array.from(document.querySelectorAll('h2, h3'));
            headers.forEach(h => {
                let next = h.nextElementSibling;
                let foundImage = null;
                let foundText = "";
                let count = 0;
                while (next && count < 8) {
                    const img = next.querySelector('img');
                    if (img && !foundImage) foundImage = img.src;
                    if (next.tagName === 'P' && !foundText) foundText = next.innerText;
                    if (next.tagName === 'H2' || next.tagName === 'H3') break;
                    next = next.nextElementSibling;
                    count++;
                }
                results.push({ title: h.innerText, image: foundImage, text: foundText });
            });
            return results;
        }''')
        
        print(json.dumps(content, indent=2))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_view())
