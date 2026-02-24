import asyncio
from playwright.async_api import async_playwright

async def test_handshake(name, url):
    print(f"Testing {name} at {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            # Use domcontentloaded instead of networkidle as some trackers never stop
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            status = response.status if response else "Unknown"
            print(f"{name} Status: {status}")
            
            # Wait a few seconds for hydration/Cloudflare
            await asyncio.sleep(5)
            
            if status == 200:
                print(f"Successfully reached {name} via Playwright.")
                return True
        except Exception as e:
            print(f"Error reaching {name}: {e}")
        finally:
            await browser.close()
    return False

async def main():
    b_ok = await test_handshake("Ben's Bites", "https://www.bensbites.com/")
    r_ok = await test_handshake("The Rundown AI", "https://www.therundown.ai/")
    red_ok = await test_handshake("Reddit AI", "https://www.reddit.com/r/ArtificialInteligence/new/")
    
    if b_ok and r_ok and red_ok:
        print("\nPLAYWRIGHT LINK HANDSHAKE SUCCESSFUL")
    else:
        print("\nPLAYWRIGHT LINK HANDSHAKE FAILED")

if __name__ == "__main__":
    asyncio.run(main())
