import asyncio
import os
import logging
import threading
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

bot = Bot(token=TOKEN)
dp = Dispatcher()
users_db = {} 

# --- PULLIK MATERIALLAR BAZASI ---
PREMIUM_MATERIALS = {
    "math_pro": {"name": "📐 Matematika: 7-sinf 'Funksiyalar' ochiq dars", "price": 5000, "link": "https://prezi.com/math-open-lesson"},
    "phys_pro": {"name": "🧲 Fizika: 9-sinf 'Magnit maydoni' tayyor slayd", "price": 7000, "link": "https://slideshare.com/physics-9"},
    "eng_pro": {"name": "🇬🇧 English: Grade 5 'My Family' creative lesson", "price": 4000, "link": "https://google.com/drive/eng-5"}
}

# --- MENU ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="👨‍🏫 O'qituvchilar (Pullik materiallar)"))
    builder.row(types.KeyboardButton(text="🎮 Interaktiv O'yin-Darslar"))
    builder.row(types.KeyboardButton(text="📚 Maktab Darsliklari"), types.KeyboardButton(text="🧠 Bilim Sinash"))
    builder.row(types.KeyboardButton(text="💰 Hamyon"), types.KeyboardButton(text="💎 VIP Bo'lim"))
    builder.row(types.KeyboardButton(text="👫 Do'stlarni taklif qilish"))
    return builder.as_markup(resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 1000} # Bonus 1000 so'm yangi foydalanuvchiga
    await message.answer("🎓 *Milliy Ta'lim va Biznes Platformasi!*\n\nProfessional ochiq darslar va metodik qo'llanmalar bo'limi ochildi!", parse_mode="Markdown", reply_markup=main_menu())

# --- O'QITUVCHILAR UCHUN PULLIK BO'LIM ---
@dp.message(F.text == "👨‍🏫 O'qituvchilar (Pullik materiallar)")
async def show_premium(message: types.Message):
    builder = InlineKeyboardBuilder()
    for key, item in PREMIUM_MATERIALS.items():
        builder.row(types.InlineKeyboardButton(text=f"{item['name']} - {item['price']} so'm", callback_data=f"buy_{key}"))
    await message.answer("💎 *EKSKLUZIV MATERIALLAR:*\n\nKerakli ochiq dars materialini tanlang. Sotib olganingizdan so'ng yuklab olish havolasi ochiladi.", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def process_purchase(callback: types.CallbackQuery):
    item_key = callback.data.split("_")[1]
    item = PREMIUM_MATERIALS[item_key]
    user_id = callback.from_user.id
    
    if user_id not in users_db: users_db[user_id] = {"balance": 0}
    
    user_balance = users_db[user_id]["balance"]
    
    if user_balance >= item["price"]:
        users_db[user_id]["balance"] -= item["price"]
        text = (
            f"✅ *Xarid muvaffaqiyatli amalga oshdi!*\n\n"
            f"📦 *Material:* {item['name']}\n"
            f"🔗 *Yuklab olish havolasi:* [SHU YERNI BOSING]({item['link']})\n\n"
            f"💰 *Qolgan balansingiz:* `{users_db[user_id]['balance']} so'm`"
        )
        await callback.message.edit_text(text, parse_mode="Markdown")
    else:
        text = (
            f"❌ *Mablag' yetarli emas!*\n\n"
            f"Narxi: `{item['price']} so'm`\n"
            f"Sizda: `{user_balance} so'm` bor.\n\n"
            "Pul ishlash uchun do'stlarni taklif qiling yoki hamyoningizni to'ldiring."
        )
        await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.text == "💰 Hamyon")
async def wallet(message: types.Message):
    balance = users_db.get(message.from_user.id, {"balance": 0})["balance"]
    await message.answer(f"💳 *Sizning balansingiz:* `{balance} so'm`", parse_mode="Markdown")

# --- RENDER WEB SERVER ---
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
