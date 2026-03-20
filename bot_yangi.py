import asyncio
import os
import logging
import random
import aiohttp
import base64
import urllib.parse
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import aiosqlite
import asyncpg
from aiohttp import web

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN", "8213419235:AAExR7swbjYl18CnGtJUzemWuw694-X2VMQ")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6363231317"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DB_URL = os.environ.get("DATABASE_URL")  # PostgreSQL URL (e.g. Neon, Supabase)
DB_FILE = "school_bot.db"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://zukko-yordamchi.onrender.com")

# --- DATABASE HELPERS ---
db_pool = None

def sql_dialect(query):
    """SQLite (?) -> PostgreSQL ($1, $2) konvertatsiya qiladi."""
    if DB_URL:
        placeholder_count = query.count('?')
        for i in range(1, placeholder_count + 1):
            query = query.replace('?', f'${i}', 1)
        query = query.replace('AUTOINCREMENT', '')
    return query

async def init_db():
    global db_pool
    if DB_URL:
        try:
            # Render/Neon uchun SSL talab qilinishi mumkin
            db_pool = await asyncpg.create_pool(
                DB_URL.replace("postgres://", "postgresql://", 1),
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("PostgreSQL pool faollashdi.")
        except Exception as e:
            logger.error(f"PostgreSQL ulanishda xatolik: {e}")

    # Jadvallarni yaratish
    create_users = "CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, username TEXT, reg_date TEXT)"
    if DB_URL:
        create_tasks = "CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, user_id BIGINT, task_text TEXT, remind_time TEXT, created_at TEXT, is_done BOOLEAN DEFAULT FALSE)"
    else:
        create_tasks = "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id BIGINT, task_text TEXT, remind_time TEXT, created_at TEXT, is_done BOOLEAN DEFAULT 0)"
    
    await db_exec(create_users)
    await db_exec(create_tasks)
    logger.info("Database jadvallari tekshirildi.")

async def db_exec(query, *args):
    query = sql_dialect(query)
    try:
        if DB_URL and db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute(query, *args)
        else:
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute(query, *args)
                await db.commit()
    except Exception as e:
        logger.error(f"DB Exec Error: {e} | Query: {query}")

async def db_fetch(query, *args, one=False):
    query = sql_dialect(query)
    try:
        if DB_URL and db_pool:
            async with db_pool.acquire() as conn:
                if one:
                    return await conn.fetchrow(query, *args)
                return await conn.fetch(query, *args)
        else:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute(query, *args) as cursor:
                    if one:
                        return await cursor.fetchone()
                    return await cursor.fetchall()
    except Exception as e:
        logger.error(f"DB Fetch Error: {e} | Query: {query}")
        return None

# --- AI HELPERS ---
async def ask_gemini(question: str) -> str:
    clean_question = question.split("Masalan:")[-1].replace("•", "").strip() or question
    if GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": clean_question}]}]}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]
        except: pass
    return await ask_pollinations(clean_question)

async def ask_pollinations(question: str) -> str:
    system = "Sen o'zbek maktab o'quvchilariga yordam beruvchi AI assistantsan. Faqat o'zbek tilida javob ber."
    encoded = urllib.parse.quote(question)
    url = f"https://text.pollinations.ai/{encoded}?model=openai&system={urllib.parse.quote(system)}&json=false"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200: return await resp.text()
    except: pass
    return "❌ AI bilan bog'lanishda muammo bo'ldi."

async def solve_test_from_image(image_buffer: bytes) -> str:
    img_b64 = base64.b64encode(image_buffer).decode("utf-8")
    if GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [
                {"text": "Ushbu rasmdagi savol/testni tahlil qil va o'zbek tilida yechib ber."},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]}]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]
        except: pass
    return "❌ Rasmni o'qishda xatolik."

# --- DATA ---
EDUPORTAL_IDS = {"1": "8", "2": "9", "3": "13", "4": "12", "5": "14", "6": "6", "7": "7", "8": "17", "9": "18", "10": "11", "11": "19"}
BOOKS_DATA = {str(i): [
    ("🏛 Kitob.uz", f"https://kitob.uz/uz/library?genre=145&subgenre={145 + i}"),
    ("📘 Eduportal", f"http://eduportal.uz/Eduportal/batafsil1/{EDUPORTAL_IDS.get(str(i))}?menu=33"),
    ("📖 InfoEdu", f"https://infoedu.uz/category/darsliklar/{i}-sinf/"),
] for i in range(1, 12)}

KREATIV_GAMES = {
    "Matematika": {"🧩 Domino": "Amallar bajarish musobaqasi.", "🏁 Poyga": "Og'zaki hisob poygasi."},
    "Ona tili": {"📝 So'z yasash": "Uzun so'zdan yangi so'zlar tuzish.", "🔍 Xato top": "Imlo xatolarini topish."},
    "English": {"🐝 Spelling Bee": "So'zlarni harflash.", "📸 Flashcards": "Rasmli lug'at."},
    "Tarix": {"⏳ Sayohat": "Tarixiy sanalar o'yini.", "👑 Shaxslar": "Buyuk siymolarni topish."},
    "Metodlar": {"💡 Aqliy hujum": "Tezkor savol-javob.", "🎨 Sinkveyn": "5 qatorli she'r."}
}

STARTUP_DATA = {"🚀 Nima u?": "Innovatsion biznes loyiha.", "💡 G'oya": "Muammoga yechim toping.", "💻 IT": "Bilim oling: it-park.uz"}
MOTIVATION_DATA = ["🌟 Ilm — najotdir!", "🚀 Eng katta sarmoya — olovingizga!", "💡 Xatolar — tajriba."]
GAMES_DATA = [{"q": "Eng baland cho'qqi?", "a": "Everest", "o": ["Everest", "K2", "Monblan"]}]
FACTS_DATA = ["🍯 Asal buzilmaydi.", "🐙 Qoni ko'k.", "🦒 30 daqiqa uxlashadi."]

# --- BOT LOGIC ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
ai_sessions = set()

def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎨 Kreativ darslar"))
    builder.row(types.KeyboardButton(text="📚 Darsliklar (1-11)"), types.KeyboardButton(text="🧩 Bilim testi"))
    builder.row(types.KeyboardButton(text="📊 BSB (Nazorat)"), types.KeyboardButton(text="📅 Taqvim rejalar"))
    builder.row(types.KeyboardButton(text="🎥 Video darslar"), types.KeyboardButton(text="📝 Onlayn testlar"))
    builder.row(types.KeyboardButton(text="🤖 AI Yordamchi"), types.KeyboardButton(text="💡 Motivatsiya"))
    builder.row(types.KeyboardButton(text="🌍 G'aroyib Faktlar"), types.KeyboardButton(text="📝 Vazifalarim"))
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    reg_date = datetime.now().strftime("%Y-%m-%d")
    await db_exec("INSERT INTO users (user_id, username, reg_date) VALUES (?, ?, ?) ON CONFLICT (user_id) DO NOTHING", 
                  message.from_user.id, message.from_user.username, reg_date)
    await message.answer("👋 *Salom!* 'ZUKKO YORDAMCHI'ga xush kelibsiz! 🚀", parse_mode="Markdown", reply_markup=main_menu())

@dp.message(F.text == "💡 Motivatsiya")
async def show_motiv(m: types.Message): await m.answer(random.choice(MOTIVATION_DATA))

@dp.message(F.text == "🌍 G'aroyib Faktlar")
async def show_fact(m: types.Message): await m.answer(f"💡 *BILASIZMI?*\n\n{random.choice(FACTS_DATA)}", parse_mode="Markdown")

@dp.message(F.text == "📚 Darsliklar (1-11)")
async def show_grades(m: types.Message):
    builder = InlineKeyboardBuilder()
    for g in range(1, 12): builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"gr_{g}"))
    builder.adjust(3)
    await m.answer("📁 *Sinfingizni tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("gr_"))
async def show_books(c: types.CallbackQuery):
    grade = c.data.split('_')[1]
    builder = InlineKeyboardBuilder()
    for n, l in BOOKS_DATA.get(grade, []): builder.row(types.InlineKeyboardButton(text=n, url=l))
    await c.message.edit_text(f"📚 *{grade}-sinf darsliklari:*", reply_markup=builder.as_markup())

@dp.message(F.text == "📊 BSB (Nazorat)")
async def bsb_section(m: types.Message):
    builder = InlineKeyboardBuilder()
    for g in range(5, 12): builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"bsb_{g}"))
    builder.adjust(3)
    await m.answer("📊 *BSB bo'limi:* Sinfingizni tanlang 👇", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("bsb_"))
async def show_bsb(c: types.CallbackQuery):
    grade = c.data.split('_')[1]
    await c.message.edit_text(f"📊 *{grade}-sinf BSB bo'limi*\n\nTest rasmiga olib yuboring, AI yechib beradi! 🤖")

@dp.message(F.text == "📅 Taqvim rejalar")
async def taqvim_section(m: types.Message):
    builder = InlineKeyboardBuilder()
    for g in range(1, 12): builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"taqvim_{g}"))
    builder.adjust(3)
    await m.answer("📅 *Taqvim-mavzu rejalar:*", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("taqvim_"))
async def show_taqvim(c: types.CallbackQuery):
    await c.message.edit_text("📅 Rejalarni [Maktab.uz](https://maktab.uz/) portalidan yuklab olishingiz mumkin.", parse_mode="Markdown")

@dp.message(F.text == "🤖 AI Yordamchi")
async def ai_cmd(m: types.Message):
    ai_sessions.add(m.from_user.id)
    await m.answer("🤖 *AI rejimi faollashdi!* Savolingizni yozing.", parse_mode="Markdown")

@dp.message(F.text == "📝 Vazifalarim")
async def show_tasks(m: types.Message):
    tasks = await db_fetch("SELECT task_text, remind_time FROM tasks WHERE user_id = ? AND is_done = ?", 
                           m.from_user.id, False if DB_URL else 0)
    if not tasks: return await m.answer("📝 Vazifalar yo'q.")
    res = "📝 *VAZIFALAR:* \n\n" + "\n".join([f"📌 {t[0]} ({t[1]})" for t in tasks])
    await m.answer(res, parse_mode="Markdown")

@dp.message(F.photo)
async def handle_photo(m: types.Message):
    msg = await m.answer("⏳ _AI rasm tahlil qilinmoqda..._")
    file = await bot.get_file(m.photo[-1].file_id)
    buf = await bot.download_file(file.file_path)
    res = await solve_test_from_image(buf.read())
    await msg.edit_text(f"✅ *JAVOB:* \n\n{res}", parse_mode="Markdown")

@dp.message()
async def handle_text(m: types.Message):
    if m.from_user.id in ai_sessions:
        msg = await m.answer("🤖 _AI o'ylanmoqda..._")
        res = await ask_gemini(m.text)
        await msg.edit_text(f"🤖 *AI:* \n\n{res}", parse_mode="Markdown")
    elif not m.text.startswith("/"):
        await m.answer("Kerakli bo'limni tanlang 👇", reply_markup=main_menu())

# --- INFRASTRUCTURE ---
async def reminder_loop():
    while True:
        now = datetime.now().strftime("%H:%M")
        res = await db_fetch("SELECT id, user_id, task_text FROM tasks WHERE remind_time = ? AND is_done = ?", 
                             now, False if DB_URL else 0)
        if res:
            for r in res:
                try:
                    await bot.send_message(r[1], f"⏰ *Eslatma:* {r[2]}")
                    await db_exec("UPDATE tasks SET is_done = ? WHERE id = ?", True if DB_URL else 1, r[0])
                except: pass
        await asyncio.sleep(60)

async def keep_alive():
    """Render uxlab qolmasligi uchun."""
    while True:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(RENDER_URL) as r:
                    logger.info(f"Self-ping: {r.status}")
        except: pass
        await asyncio.sleep(300)

async def handle_web(request): return web.Response(text="Bot runs! 🚀")

async def main():
    await init_db()
    asyncio.create_task(reminder_loop())
    asyncio.create_task(keep_alive())
    
    # Web server for Render health check
    app = web.Application()
    app.router.add_get("/", handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
