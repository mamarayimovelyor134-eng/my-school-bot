import asyncio
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import LabeledPrice, PreCheckoutQuery

logging.basicConfig(level=logging.INFO)

# --- KONFIGURATSIYA ---
TOKEN = os.environ.get("BOT_TOKEN")
PAYMENT_PROVIDER_TOKEN = "399304918:TEST:92243" 
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

bot = Bot(token=TOKEN)
dp = Dispatcher()
users_db = {} 

# --- ASOSIY MENYU ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📚 Maktab Darsliklari"))
    builder.row(types.KeyboardButton(text="🎮 Interaktiv O'yin-Darslar"))
    builder.row(types.KeyboardButton(text="💰 Hamyonni to'ldirish"))
    builder.row(types.KeyboardButton(text="💳 Balansni tekshirish"), types.KeyboardButton(text="👫 Referallar"))
    return builder.as_markup(resize_keyboard=True)

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 1000}
    await message.answer("🎓 *Milliy Ta'lim Platformasiga xush kelibsiz!*", parse_mode="Markdown", reply_markup=main_menu())

# --- RENDER WEB SERVER (UYG'OTISH UCHUN) ---
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")
    def log_message(self, *a): pass

def run_web():
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Server {port}-portda ishlamoqda...")
    HTTPServer(("0.0.0.0", port), H).serve_forever()

def self_ping():
    """Bot o'zini o'zi uyg'otib turishi uchun (Ichki tizim)"""
    import time
    time.sleep(30)
    while True:
        try:
            if RENDER_URL:
                # Haqiqiy so'rov ko'rinishida yuboramiz
                req = Request(RENDER_URL, headers={'User-Agent': 'Mozilla/5.0'})
                urlopen(req, timeout=10)
                logging.info("Self-ping muvaffaqiyatli!")
        except Exception as e:
            logging.error(f"Self-ping xatosi: {e}")
        time.sleep(300) # Har 5 daqiqada

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Web serverni alohida oqimda ishga tushiramiz
    threading.Thread(target=run_web, daemon=True).start()
    # O'zini uyg'otish tizimini ishga tushiramiz
    threading.Thread(target=self_ping, daemon=True).start()
    # Botni ishga tushiramiz
    asyncio.run(main())
