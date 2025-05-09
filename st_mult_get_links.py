import asyncio
import time
from playwright.async_api import async_playwright
from email_maps_parser import db_st

t = time.time()
db_lock = asyncio.Lock()

async def sem_task(sem, url):
    async with sem:
        await run_playwright_task(url)

async def run_playwright_task(url):
    async with async_playwright() as p:
        add_bd = []
        names_web = []
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)

        scrollable_selector = "//div[@class='m6QErb DxyBCb kA9KIf dS8AEf XiKgde ecceSd']"
        scrollable = await page.wait_for_selector(scrollable_selector)

        await scrollable.hover()

        prev_height = 0
        no_change_timer_start = None
        scroll_step = 50  # менший крок для плавності
        delay = 0.1         # коротша пауза між кроками

        while True:
            await page.mouse.wheel(0, scroll_step)
            await asyncio.sleep(delay)

            end_marker = page.locator(
                "//span[@class='HlvSq' and contains(text(), 'Ви переглянули весь список.')]")
            if await end_marker.is_visible():
                print("Знайдено кінець списку.")
                break

            new_height = await page.evaluate(
                "(el) => el.scrollHeight", scrollable)

            if new_height == prev_height:
                if no_change_timer_start is None:
                    no_change_timer_start = time.time()
                elif time.time() - no_change_timer_start >= 30:
                    print("3 хвилини без змін — оновлюємо сторінку...")
                    await page.reload()
                    scrollable = await page.wait_for_selector(scrollable_selector)
                    await scrollable.hover()
                    prev_height = 0
                    no_change_timer_start = None
                    continue
            else:
                prev_height = new_height
                no_change_timer_start = None

        elements = page.locator("//a[@class='hfpxzc']")
        count = await elements.count()

        for i in range(count):
            text = await elements.nth(i).get_attribute("href")
            name_web = await elements.nth(i).get_attribute("aria-label")
            add_bd.append(text)
            names_web.append(name_web)

        async with db_lock:
            await db_st.init_db()
            for i in range(len(add_bd)):
                await db_st.insert_item(add_bd[i], names_web[i].lower())

        await browser.close()

async def main(urls, max_concurrent_tasks):
    sem = asyncio.Semaphore(max_concurrent_tasks)
    tasks = [sem_task(sem, url) for url in urls]
    await asyncio.gather(*tasks)

urls = [
    "https://www.google.com/maps/search/ssd+львів/...",
    "https://www.google.com/maps/search/ssd+київ/...",
    "https://www.google.com/maps/search/ssd+харків/...",
    "https://www.google.com/maps/search/ssd+Дніпро/...",
]

num_threads = 3

asyncio.run(main(urls, num_threads))
print("Час виконання:", time.time() - t)
