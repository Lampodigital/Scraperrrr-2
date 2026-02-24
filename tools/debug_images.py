import asyncio
import json
from playwright.async_api import async_playwright

async def debug_images():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # --- Test Rundown ---
        print("=== THE RUNDOWN AI ===")
        context_r = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        try:
            with open("/Users/stefanorossi/Documents/Scraperrrr 2/.tmp/cookies_rundown.json") as f:
                await context_r.add_cookies(json.load(f))
        except: pass
        
        page_r = await context_r.new_page()
        await page_r.goto("https://www.therundown.ai/p/what-openai-and-jony-ive-are-building", wait_until="domcontentloaded")
        await asyncio.sleep(4)
        
        all_imgs = await page_r.evaluate('''() => {
            return Array.from(document.querySelectorAll('img')).map(img => ({
                src: img.src,
                alt: img.alt,
                width: img.naturalWidth,
                height: img.naturalHeight
            })).filter(i => i.src && i.width > 50);
        }''')
        print(f"Found {len(all_imgs)} images (>50px wide):")
        for img in all_imgs[:10]:
            print(f"  {img['width']}x{img['height']} | {img['src'][:100]}")
        
        await context_r.close()
        
        # --- Test Ben's Bites ---
        print("\n=== BEN'S BITES ===")
        context_b = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        try:
            with open("/Users/stefanorossi/Documents/Scraperrrr 2/.tmp/cookies_bensbites.json") as f:
                await context_b.add_cookies(json.load(f))
        except: pass
        
        page_b = await context_b.new_page()
        await page_b.goto("https://www.bensbites.com/p/big-upgrade-for-sonnet", wait_until="domcontentloaded")
        await asyncio.sleep(4)
        
        all_imgs_b = await page_b.evaluate('''() => {
            return Array.from(document.querySelectorAll('img')).map(img => ({
                src: img.src,
                alt: img.alt,
                width: img.naturalWidth,
                height: img.naturalHeight
            })).filter(i => i.src && i.width > 50);
        }''')
        print(f"Found {len(all_imgs_b)} images (>50px wide):")
        for img in all_imgs_b[:10]:
            print(f"  {img['width']}x{img['height']} | {img['src'][:100]}")
        
        # Also check Open Graph meta tags as fallback
        og_img = await page_b.evaluate('''() => {
            const meta = document.querySelector('meta[property="og:image"], meta[name="twitter:image"]');
            return meta ? meta.getAttribute("content") : null;
        }''')
        print(f"\nOG Image: {og_img}")
        
        await context_b.close()
        await browser.close()

asyncio.run(debug_images())
