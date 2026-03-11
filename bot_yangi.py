import asyncio
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
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

# --- MARKET BAZASI ---
PREMIUM_MATERIALS = {
    "math_pro": {"name": "📐 Matematika: Ochiq dars", "price": 5000, "link": "https://edu.uz/math"},
    "phys_pro": {"name": "🧲 Fizika: Tayyor slayd", "price": 7000, "link": "https://edu.uz/phys"}
}

# --- ASOSIY MENYU ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="👨‍🏫 O'qituvchilar (Market)"))
    builder.row(types.KeyboardButton(text="💰 Hamyonni to'ldirish (CLICK/PAYME)"))
    builder.row(types.KeyboardButton(text="💳 Balansni tekshirish"), types.KeyboardButton(text="🎮 O'yinlar"))
    builder.row(types.KeyboardButton(text="👫 Referallar"))
    return builder.as_markup(resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 1000}
    await message.answer("🚀 *Milliy Ta'lim Platformasi Faol!*", parse_mode="Markdown", reply_markup=main_menu())

# --- TO'LOV TIZIMI (CLICK/PAYME) ---
@dp.message(F.text == "💰 Hamyonni to'ldirish (CLICK/PAYME)")
async def fill_wallet(message: types.Message):
    await message.answer(
        "💳 *To'lov miqdorini tanlang:*",
        reply_markup=InlineKeyboardBuilder()
        .row(types.InlineKeyboardButton(text="💵 5,000 so'm", callback_data="pay_5000"))
        .row(types.InlineKeyboardButton(text="💵 10,000 so'm", callback_data="pay_10000"))
        .row(types.InlineKeyboardButton(text="💵 20,000 so'm", callback_data="pay_20000"))
        .as_markup()
    )

@dp.callback_query(F.data.startswith("pay_"))
async def create_invoice(callback: types.CallbackQuery):
    amount = int(callback.data.split("_")[1])
    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Hamyonni to'ldirish",
            description=f"Balansingizni {amount} so'mga to'ldirasiz.",
            payload=f"wallet_refill_{amount}",
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency="UZS",
            prices=[LabeledPrice(label="To'ldirish", amount=amount * 100)]
        )
    except Exception as e:
        await callback.message.answer(f"❌ To'lov xatosi: Provider Token noto'g'ri bo'lishi mumkin.")
        logging.error(f"Payment error: {e}")
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: types.Message):
    amount = message.successful_payment.total_amount // 100
    user_id = message.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 0}
    users_db[user_id]["balance"] += amount
    await message.answer(f"✅ Hamyoningizga `{amount} so'm` qo'shildi.")

# --- RENDER WEB SERVER & KEEP ALIVE ---
class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

def run_web():
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Web server starting on port {port}")
    HTTPServer(("0.0.0.0", port), H).serve_forever()

def keep_alive():
    import time
    time.sleep(20) # Start after web server
    while True:
        try:
            if RENDER_URL:
                urlopen(RENDER_URL, timeout=10)
                logging.info("Keep-alive ping sent")
        except: pass
        time.sleep(600)

async def main():
    logging.info("Starting bot polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    asyncio.run(main())
