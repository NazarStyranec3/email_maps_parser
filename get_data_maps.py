import asyncio
import re
from playwright.async_api import async_playwright
from email_maps_parser import add_exsl, db_st

from playwright.async_api import TimeoutError as PlaywrightTimeoutError


db_lock = asyncio.Lock()

async def run_playwright_task(item):
    item_id, url, name = item
    print(f"URL: {url}, Name: {name}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            await page.goto(url, timeout=15000)
        except PlaywrightTimeoutError:
            print("Тайм-аут при завантаженні сторінки.")
            await browser.close()
            return

        await asyncio.sleep(3)

        try:
            element_locator = page.locator("//a[@data-tooltip='Перейти на веб-сайт']")
            link = await element_locator.first.get_attribute('href') if await element_locator.count() > 0 else 'None'
        except:
            link = 'None'

        print(link)

        if link != 'None':
            try:
                scrollable = page.locator("//button[@data-tooltip='Копіювати номер телефону']//div[@class='rogA2c ']")
                element = await scrollable.element_handle()
                if element:
                    await page.evaluate("(el) => el.scrollHeight", element)
            except Exception as e:
                print(f"Помилка під час прокрутки: {e}")

            try:
                phono_number_maps = await page.locator("//button[@data-tooltip='Копіювати номер телефону']//div[@class='rogA2c ']").text_content()
            except Exception as e:
                print(f"Помилка при отриманні номера телефону: {e}")
                phono_number_maps = 'None'

            try:
                await page.goto(link, timeout=15000)
                await page.wait_for_timeout(3000)
                page_text = await page.text_content("body")
            except:
                page_text = ''

            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', page_text or "")
            phones = re.findall(r'(?:\+380|0)\s?\(?\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', page_text or "")
        else:
            phono_number_maps = 'None'
            emails = []
            phones = []

        print('Назва з карти:', name)
        print('Телефон з карти:', phono_number_maps)
        print("Email-и зі сайту:", emails)
        print("Телефони зі сайту:", phones)
        print('*' * 15)

        await asyncio.sleep(2)

        add_exsl.add_ex([url, link, name, phono_number_maps, emails, phones])
        await db_st.update_status_to_ok(item_id)
        print(f"Статус оновлено для ID {item_id} -> OK\n")

        await browser.close()

async def start_tasks_limited(items, max_concurrent):
    sem = asyncio.Semaphore(max_concurrent)

    async def sem_task(item):
        async with sem:
            await run_playwright_task(item)

    tasks = [sem_task(item) for item in items]
    await asyncio.gather(*tasks)

async def main():
    items = await db_st.get_items_with_null_status()
    num_threads = 6
    await start_tasks_limited(items, num_threads)

asyncio.run(main())

