import asyncio
import os
from telegram import Bot
from playwright.async_api import async_playwright

# GitHub Secrets থেকে টোকেন এবং চ্যাট আইডি নেওয়া হবে
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

PRODUCTS = [
    {
        "name": "JapanNext 4K Monitor",
        "url": "https://www.amazon.de/-/en/JapanNext-Delivery-Adjustment-Integrated-JN-IPS27UHDR-C65W-HSP-W/dp/B0CTKDS77H/",
    },
    {
        "name": "darkFlash PC Case",
        "url": "https://www.amazon.de/-/en/darkFlash-Mid-Tower-Surfaces-Pre-Installed-Compatible-White/dp/B0DRRWSZR6/",
    },
    {
        "name": "Phanteks CPU Cooler",
        "url": "https://www.amazon.de/Phanteks-GLACIER-360D30-X2-Cooling/dp/B0F4QGPFBJ/",
    },
]

async def get_amazon_price(page, url):
    try:
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(3000)

        price_whole = await page.locator(".a-price-whole").first.inner_text()
        price_fraction = await page.locator(".a-price-fraction").first.inner_text()

        price_str = f"{price_whole.strip()}.{price_fraction.strip()}"
        price_float = float(price_str.replace(".", "").replace(",", "."))
        return price_float
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for product in PRODUCTS:
            print(f"Checking price for: {product['name']}...")
            current_price = await get_amazon_price(page, product["url"])

            if current_price:
                print(f"Current Price: €{current_price}")
                message = f"📦 **Amazon Price Update**\n🔹 {product['name']}\n💰 বর্তমান দাম: €{current_price}\n🔗 {product['url']}"
                await bot.send_message(chat_id=CHAT_ID, text=message)

            await asyncio.sleep(5)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
