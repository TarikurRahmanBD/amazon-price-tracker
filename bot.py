import asyncio
import json
import os
import requests
from playwright.async_api import async_playwright
from telegram import Bot

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)


def load_products():
  with open("products.json", "r", encoding="utf-8") as f:
    return json.load(f)


def get_eur_to_bdt_rate():
  try:
    response = requests.get("https://open.er-api.com/v6/latest/EUR", timeout=10)
    data = response.json()
    if data and "rates" in data and "BDT" in data["rates"]:
      return float(data["rates"]["BDT"])
  except Exception as e:
    print(f"Error fetching exchange rate: {e}")
  return 128.0


async def get_amazon_price(page, url):
  try:
    # Amazon-কে আসল ব্রাউজার দেখানোর জন্য কুকিজ ও হেডার সেটিংস
    await page.goto(url, timeout=90000, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    # যদি Amazon এর কোনো Cookie Banner আসে তবে Accept করার চেষ্টা করবে
    try:
      accept_btn = page.locator("#sp-cc-accept")
      if await accept_btn.is_visible():
        await accept_btn.click()
        await page.wait_for_timeout(1000)
    except Exception:
      pass

    price_float = None

    # ১. প্রথম উপায়: স্ট্যান্ডার্ড অ্যামাজন প্রাইস ফর্মেট (.a-price-whole & .a-price-fraction)
    try:
      price_whole_elem = page.locator(".a-price-whole").first
      if await price_whole_elem.is_visible():
        price_whole = await price_whole_elem.inner_text()
        price_fraction = await page.locator(".a-price-fraction").first.inner_text()
        price_str = f"{price_whole.strip()}.{price_fraction.strip()}"
        price_float = float(price_str.replace("\n", "").replace(".", "").replace(",", "."))
    except Exception:
      price_float = None

    # ২. দ্বিতীয় উপায়: অফস্ক্রিন বা ডিল প্রাইস টেক্সট (.a-offscreen)
    if not price_float:
      try:
        offscreen_elem = page.locator("span.a-price span.a-offscreen").first
        if await offscreen_elem.is_visible():
          raw_price = await offscreen_elem.inner_text()
          # "249,99€" বা "€249.99" ফরম্যাট ক্লিন করা
          cleaned = (
              raw_price.replace("€", "")
              .replace("EUR", "")
              .replace("\xa0", "")
              .strip()
          )
          cleaned = cleaned.replace(".", "").replace(",", ".")
          price_float = float(cleaned)
      except Exception:
        price_float = None

    return price_float

  except Exception as e:
    print(f"Error scraping {url}: {e}")
    return None


async def main():
  products = load_products()
  eur_to_bdt = get_eur_to_bdt_rate()

  async with async_playwright() as p:
    # রিয়েল ব্রাউজারের মতো পরিচয় তৈরি করা
    browser = await p.chromium.launch(
        headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
    )
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1366, "height": 768},
        locale="en-US",
    )
    page = await context.new_page()

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
        current_price_bdt = current_price_eur * eur_to_bdt
        print(
            f"Success: €{current_price_eur:.2f} ({current_price_bdt:.2f} BDT)"
        )

        message += (
            f"📦 **{product['name']}**\n"
            f"💶 EUR দাম: €{current_price_eur:.2f}\n"
            f"৳ BDT দাম: ৳{current_price_bdt:,.2f} BDT\n"
            f"🔗 [Amazon Link]({product['url']})\n\n"
        )
      else:
        print(f"Failed to fetch price for: {product['name']}")

      await asyncio.sleep(8)

    if success_count > 0:
      await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
      print("Telegram message sent successfully!")
    else:
      print("No prices fetched successfully, skipping telegram message.")

    await browser.close()


if __name__ == "__main__":
  asyncio.run(main())
