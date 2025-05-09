import os
import aiosqlite


DB_PATH = os.path.join("../data.db")


# Функція для ініціалізації бази даних
async def init_db():
    async with aiosqlite.connect(DB_PATH, check_same_thread=False) as conn:  # Додано check_same_thread=False
        cursor = await conn.cursor()
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT DEFAULT NULL,
                name TEXT NOT NULL UNIQUE,
                link TEXT NOT NULL UNIQUE
            )
        """)
        await conn.commit()

# Функція для вставки елемента в БД
async def insert_item(link: str, name: str):
    async with aiosqlite.connect(DB_PATH, check_same_thread=False) as db:  # Додано check_same_thread=False
        async with db.execute("SELECT 1 FROM items WHERE name = ? LIMIT 1", (name,)) as cursor:
            if await cursor.fetchone():
                print(f"[!] Існує: {name}")
                return
        await db.execute("INSERT INTO items (link, name, status) VALUES (?, ?, NULL)", (link, name))
        await db.commit()
        print(f"[+] Додано: {name} ({link})")

# Функція для отримання елементів з null статусом
async def get_items_with_null_status():
    async with aiosqlite.connect(DB_PATH, check_same_thread=False) as db:  # Додано check_same_thread=False
        async with db.execute("SELECT id, link, name FROM items WHERE status IS NULL") as cursor:
            return await cursor.fetchall()

# Функція для оновлення статусу на OK
async def update_status_to_ok(item_id: int):
    async with aiosqlite.connect(DB_PATH, check_same_thread=False) as db:  # Додано check_same_thread=False
        await db.execute("UPDATE items SET status = 'OK' WHERE id = ?", (item_id,))
        await db.commit()

# Функція для вибору одного елемента і блокування його
async def fetch_one_item_and_lock():
    async with aiosqlite.connect(DB_PATH, check_same_thread=False) as db:  # Додано check_same_thread=False
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute("SELECT id, link, name FROM items WHERE status IS NULL LIMIT 1") as cursor:
            row = await cursor.fetchone()
        if row:
            await db.execute("UPDATE items SET status = 'IN_PROGRESS' WHERE id = ?", (row[0],))
        await db.commit()
        return row
