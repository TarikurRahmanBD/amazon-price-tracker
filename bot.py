import asyncio
import json
import os
import requests
from playwright.async_api import async_playwright
from telegram import Bot

# GitHub Secrets থেকে টোকেন এবং চ্যাট আইডি নেওয়া হবে
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)


# JSON ফাইল থেকে পণ্যের তালিকা লোড করা
def load_products():
  with open("products.json", "r", encoding="utf-8") as f:
    return json.load(f)


# লাইভ Euro to BDT exchange rate নেওয়ার ফাংশন
def get_eur_to_bdt_rate():
  try:
    response = requests.get("https://open.er-api.com/v6/latest/EUR", timeout=10)
    data = response.json()
    if data and "rates" in data and "BDT" in data["rates"]:
      return float(data["rates"]["BDT"])
  except Exception as e:
    print(f"Error fetching exchange rate: {e}")

  # যদি কোনো কারণে API ফেল করে, তবে ডিফল্ট হিসেবে ১২৮ টাকা ধরা হবে
  return 128.0


async def get_amazon_price(page, url):
  try:
    # টাইমআউট বাড়িয়ে ৯০ সেকেন্ড করা হয়েছে যাতে সার্ভার লোড নিতে সমস্যা না হয়
    await page.goto(url, timeout=90000, wait_until="domcontentloaded")
    await page.wait_for_timeout(5000)

    price_whole = await page.locator(".a-price-whole").first.inner_text()
    price_fraction = await page.locator(".a-price-fraction").first.inner_text()

    price_str = f"{price_whole.strip()}.{price_fraction.strip()}"
    price_float = float(price_str.replace(".", "").replace(",", "."))
    return price_float
  except Exception as e:
    print(f"Error scraping {url}: {e}")
    return None


async def main():
  products = load_products()
  eur_to_bdt = get_eur_to_bdt_rate()

  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = await context.new_page()

    # শুরুতেই আজকের লাইভ এক্সচেঞ্জ রেট দিয়ে মেসেজ হেডার
    message = (
        "📊 **Amazon Price & Currency Update**\n"
        f"💱 **আজকের ইউরো রেট:** 1 EUR = {eur_to_bdt:.2f} BDT\n"
        "-----------------------------------\n\n"
    )

    success_count = 0

    for product in products:
      print(f"Checking price for: {product['name']}...")
      current_price_eur = await get_amazon_price(page, product["url"])

      if current_price_eur:
        success_count += 1
        # BDT হিসাব করা (EUR × BDT Rate)
        current_price_bdt = current_price_eur * eur_to_bdt
        print(
            f"Current Price: €{current_price_eur} ({current_price_bdt:.2f} BDT)"
        )

        message += (
            f"📦 **{product['name']}**\n"
            f"💶 EUR দাম: €{current_price_eur:.2f}\n"
            f"৳ BDT দাম: ৳{current_price_bdt:,.2f} BDT\n"
            f"🔗 [Amazon Link]({product['url']})\n\n"
        )

      # পণ্যের মাঝে বিরতি বাড়িয়ে ১০ সেকেন্ড করা হলো
      await asyncio.sleep(10)

    # যদি অন্তত একটি পণ্যের দাম পাওয়া যায়, তবেই টেলিগ্রামে মেসেজ পাঠাবে
    if success_count > 0:
      await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
    else:
      print("No prices fetched successfully, skipping telegram message.")

    await browser.close()


if __name__ == "__main__":
  asyncio.run(main())
