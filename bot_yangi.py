import asyncio
import os
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite
import aiohttp
from aiohttp import web
from dotenv import load_dotenv

# --- KONFIGURATSIYA (FIXED) ---
load_dotenv()
# Tokenni to'g'ridan-to'g'ri kiritamiz (Serverda 100% ishlashi uchun)
TOKEN = "8213419235:AAHSRkAwyYIQf2MSEmiojFhzeFuDHBRwlYU"
ADMIN_ID = 6363231317
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
PORT = int(os.environ.get("PORT", "8080"))

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StableBot")

# --- DATABASE ---
DB_FILE = "school_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, username TEXT, reg_date TEXT)")
        await db.commit()
    logger.info("📦 DB initialized.")

async def add_user(uid, uname):
    now = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username, reg_date) VALUES (?, ?, ?)", (uid, uname, now))
        await db.commit()

# --- HANDLERS ---
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.row(types.KeyboardButton(text="🎨 Kreativ darslar"), types.KeyboardButton(text="📚 Darsliklar (1-11)"))
    return kb.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def start(m: types.Message):
    await add_user(m.from_user.id, m.from_user.username)
    await m.answer("🚀 *ZUKKO YORDAMCHI* botiga xush kelibsiz!\n\nBot muvaffaqiyatli tiklandi va 24/7 rejimda ishlamoqda. ✨", 
                   parse_mode="Markdown", reply_markup=main_menu())

@dp.message(F.text == "🎨 Kreativ darslar")
async def kreativ(m: types.Message):
    res = "🎨 *KREATIV DARSLAR VA METODLAR* \n\n"
    res += "🔹 *Domino metodi*: Zanjir hosil qilish o'yini.\n"
    res += "🔹 *Aqliy hujum*: Tezkor savol-javoblar.\n"
    res += "🔹 *Sinkveyn*: 5 qatorli she'riy uslub.\n"
    res += "🔹 *Wordwall*: [O'yinlar portali](https://wordwall.net/uz-uz/community/matematika)"
    await m.answer(res, parse_mode="Markdown", disable_web_page_preview=True)

@dp.message(F.text == "📚 Darsliklar (1-11)")
async def books(m: types.Message):
    res = "📚 *DARSLIKLAR PORTALLARI*\n\n"
    res += "🔹 [Kitob.uz (Rasmiy)](https://kitob.uz)\n"
    res += "🔹 [Eduportal (Elektron)](http://eduportal.uz)\n\n"
    await m.answer(res, parse_mode="Markdown")

# --- SERVER ---
async def handle_web(request): return web.Response(text="Bot runs 24/7! 🚀")

async def main():
    await init_db()
    
    # Web health server (Render asks for this)
    try:
        app = web.Application()
        app.router.add_get("/", handle_web)
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", PORT).start()
    except: pass
    
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ FINAL VERSION IS ONLINE")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
