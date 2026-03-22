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

# --- KONFIGURATSIYA ---
load_dotenv()
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
PORT = int(os.environ.get("PORT", "8080"))

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SimpleBot")

# --- STATES ---
class BotStates(StatesGroup):
    ADMIN_MSG = State()

# --- DATABASE ---
DB_FILE = "school_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, username TEXT, reg_date TEXT)")
        await db.commit()
    logger.info("📦 Ma'lumotlar bazasi tayyor.")

async def add_user(user_id, username):
    reg_date = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username, reg_date) VALUES (?, ?, ?)", (user_id, username, reg_date))
        await db.commit()

# --- KLAVIATURA ---
def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.row(types.KeyboardButton(text="🎨 Kreativ darslar"), types.KeyboardButton(text="📚 Darsliklar (1-11)"))
    return kb.as_markup(resize_keyboard=True)

# --- HANDLERLAR ---
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def cmd_start(m: types.Message, state: FSMContext):
    await state.clear()
    await add_user(m.from_user.id, m.from_user.username)
    await m.answer("🚀 *ZUKKO YORDAMCHI* botiga xush kelibsiz!\n\nBot hozirda mukammal va sodda rejimda ishlamoqda. ✨", 
                   parse_mode="Markdown", reply_markup=main_menu())

@dp.message(F.text == "🎨 Kreativ darslar")
async def show_kreativ(m: types.Message):
    res = "🎨 *KREATIV DARSLAR VA METODLAR* \n\n"
    res += "🔹 *Domino metodi*: Zanjir hosil qilish o'yini.\n"
    res += "🔹 *Aqliy hujum*: Tezkor savol-javoblar.\n"
    res += "🔹 *Sinkveyn*: 5 qatorli she'riy uslub.\n"
    res += "🔹 *Wordwall*: [O'yinlar portali](https://wordwall.net/uz-uz/community/matematika)"
    await m.answer(res, parse_mode="Markdown", disable_web_page_preview=True)

@dp.message(F.text == "📚 Darsliklar (1-11)")
async def show_books(m: types.Message):
    res = "📚 *DARSLIKLAR PORTALLARI*\n\n"
    res += "🔹 [Kitob.uz (Rasmiy)](https://kitob.uz)\n"
    res += "🔹 [Eduportal (Elektron)](http://eduportal.uz)\n\n"
    res += "Ushbu saytlardan barcha sinf darsliklarini yuklab olishingiz mumkin."
    await m.answer(res, parse_mode="Markdown", disable_web_page_preview=True)

# --- SERVER STABILITY ---
async def keep_alive():
    if not RENDER_URL: return
    while True:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(RENDER_URL) as r: pass
        except: pass
        await asyncio.sleep(600)

async def handle_web(request): return web.Response(text="Running! 🚀")

async def main():
    if not TOKEN:
        logger.critical("❌ BOT_TOKEN TOPILMADI!")
        return
    
    await init_db()
    asyncio.create_task(keep_alive())
    
    # Web server
    try:
        app = web.Application()
        app.router.add_get("/", handle_web)
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", PORT).start()
        logger.info(f"🌐 Server port {PORT} da ishga tushdi.")
    except: pass
    
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except: pass
