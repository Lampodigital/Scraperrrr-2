import asyncio
import json
from playwright.async_api import async_playwright

async def get_tags():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.therundown.ai/p/what-openai-and-jony-ive-are-building")
        await asyncio.sleep(4)
        
        # Log titles and their tags
        tags = await page.evaluate('''() => {
            const results = [];
            // Try different selectors for news titles
            const elements = document.querySelectorAll('h1, h2, h3, h4, p strong a, p a strong');
            elements.forEach(el => {
                results.push({ tag: el.tagName, text: el.innerText, html: el.outerHTML });
            });
            return results;
        }''')
        print(json.dumps(tags[:20], indent=2))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_tags())
