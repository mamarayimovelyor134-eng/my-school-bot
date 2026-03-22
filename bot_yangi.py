import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiohttp import web
from dotenv import load_dotenv

# --- ENG ODDIY KONFIGURATSIYA (DEBUG MOD) ---
load_dotenv()
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", "8080"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugBot")

# --- HANDLERLAR (BAZASIZ, FAQAT MATN) ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    kb = ReplyKeyboardBuilder()
    kb.row(types.KeyboardButton(text="🎨 Kreativ darslar"), types.KeyboardButton(text="📚 Darsliklar (1-11)"))
    await m.answer("🚀 *ZUKKO DEBUG*: Bot ishlamoqda!\n\nSizni xabaringizni oldim. Baza ulanmagan, faqat matnli rejim. ✨", 
                   parse_mode="Markdown", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text == "🎨 Kreativ darslar")
async def show_k(m: types.Message):
    await m.answer("🎨 Kreativ darslar bo'limi ishlamoqda!")

@dp.message(F.text == "📚 darsliklar (1-11)")
async def show_d(m: types.Message):
    await m.answer("📚 Darsliklar bo'limi ishlamoqda!")

# --- SERVER ---
async def handle_web(request): return web.Response(text="Bot Debug Active")

async def main():
    if not TOKEN:
        logger.critical("TOKEN YO'Q!")
        return
    
    app = web.Application()
    app.router.add_get("/", handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ DEBUGGER ISHGA TUSHDI")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
