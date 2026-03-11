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
# Bu yerga @BotFather dan olingan CLICK yoki PAYME tokeningizni qo'ying
PAYMENT_PROVIDER_TOKEN = "399304918:TEST:92243" # TEST TOKEN (Placeholder)
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
    await message.answer("🚀 *Milliy Ta'lim Platformasi - Pul To'lash Tizimi Faol!*", parse_mode="Markdown", reply_markup=main_menu())

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
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Hamyonni to'ldirish",
        description=f"Botdagi balansingizni {amount} so'mga to'ldirasiz.",
        payload=f"wallet_refill_{amount}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="UZS",
        prices=[LabeledPrice(label="To'ldirish", amount=amount * 100)] # Telegramda tiyinlarda hisoblanadi (100 = 1 so'm)
    )
    await callback.answer()

# To'lovdan oldin tekshirish
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# To'lov muvaffaqiyatli o'tganda
@dp.message(F.successful_payment)
async def success_payment(message: types.Message):
    amount = message.successful_payment.total_amount // 100
    user_id = message.from_user.id
    
    if user_id not in users_db: users_db[user_id] = {"balance": 0}
    users_db[user_id]["balance"] += amount
    
    await message.answer(f"✅ *Tabriklaymiz!* To'lov muvaffaqiyatli qabul qilindi. Hamyoningizga `{amount} so'm` qo'shildi.")

# --- HAMYON VA BALANS ---
@dp.message(F.text == "💳 Balansni tekshirish")
async def check_balance(message: types.Message):
    balance = users_db.get(message.from_user.id, {"balance": 0})["balance"]
    await message.answer(f"💳 *Joriy balansingiz:* `{balance} so'm`", parse_mode="Markdown")

# --- MARKET ---
@dp.message(F.text == "👨‍🏫 O'qituvchilar (Market)")
async def school_market(message: types.Message):
    builder = InlineKeyboardBuilder()
    for k, v in PREMIUM_MATERIALS.items():
        builder.row(types.InlineKeyboardButton(text=f"{v['name']} ({v['price']} so'm)", callback_data=f"buy_{k}"))
    await message.answer("🛒 *Market:*", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def purchase(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    item = PREMIUM_MATERIALS[key]
    u_id = callback.from_user.id
    
    if users_db.get(u_id, {"balance": 0})["balance"] >= item["price"]:
        users_db[u_id]["balance"] -= item["price"]
        await callback.message.edit_text(f"🎁 *Sotib olindi:* {item['name']}\n🔗 [Yuklab olish]({item['link']})", parse_mode="Markdown")
    else:
        await callback.message.answer("❌ Balans yetarli emas. Iltimos, hamyonni to'ldiring.")
    await callback.answer()

# --- RENDER SERVER ---
class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass
def run(): HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), H).serve_forever()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run, daemon=True).start()
    asyncio.run(main())
