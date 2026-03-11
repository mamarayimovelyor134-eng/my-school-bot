import asyncio
import os
import logging
import threading
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import LabeledPrice, PreCheckoutQuery

logging.basicConfig(level=logging.INFO)

# --- CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN")
PAYMENT_PROVIDER_TOKEN = "399304918:TEST:92243" 
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

bot = Bot(token=TOKEN)
dp = Dispatcher()
users_db = {} 

# --- DATA ---
BOOKS_DATA = {
    "1-sinf": {"Matematika": "#", "Alifbe": "#"},
    "5-sinf": {"Tarix": "#", "Adabiyot": "#"},
    "10-sinf": {"Fizika": "#", "Algebra": "#"}
}

PREMIUM_MATERIALS = {
    "math": {"name": "📐 Matematika: Ochiq dars", "price": 5000, "link": "#"},
    "phys": {"name": "🧲 Fizika: Tayyor slayd", "price": 7000, "link": "#"}
}

GAMES_DATA = [
    {"q": "15 * 4 = ?", "a": "60", "o": ["50", "60", "70"]},
    {"q": "√144 = ?", "a": "12", "o": ["10", "12", "14"]},
    {"q": "Dunyodagi eng katta okean?", "a": "Tinch", "o": ["Hind", "Tinch", "Atlantika"]}
]

# --- SIMPLE UI ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📚 Darsliklar"), types.KeyboardButton(text="🧩 O'yinlar & Testlar"))
    builder.row(types.KeyboardButton(text="👨‍🏫 O'qituvchilar bo'limi"), types.KeyboardButton(text="👤 Mening profilim"))
    return builder.as_markup(resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 1000}
    await message.answer("🎓 *Xush kelibsiz!* Kerakli bo'limni tanlang:", parse_mode="Markdown", reply_markup=main_menu())

# --- 1. DARSLIKLAR ---
@dp.message(F.text == "📚 Darsliklar")
async def grades(message: types.Message):
    builder = InlineKeyboardBuilder()
    for g in ["1", "5", "10"]: # Misol tariqasida
        builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"gr_{g}"))
    await message.answer("📁 *Sinfingizni tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("gr_"))
async def books(callback: types.CallbackQuery):
    grade = f"{callback.data.split('_')[1]}-sinf"
    data = BOOKS_DATA.get(grade, {"Darsliklar": "https://eduportal.uz"})
    builder = InlineKeyboardBuilder()
    for name, link in data.items():
        builder.row(types.InlineKeyboardButton(text=f"📖 {name}", url=link))
    await callback.message.edit_text(f"📚 *{grade} darsliklari:*", parse_mode="Markdown", reply_markup=builder.as_markup())

# --- 2. O'YINLAR (GAMIFICATION) ---
@dp.message(F.text == "🧩 O'yinlar & Testlar")
async def play(message: types.Message):
    quiz = random.choice(GAMES_DATA)
    builder = InlineKeyboardBuilder()
    for o in quiz["o"]:
        builder.add(types.InlineKeyboardButton(text=o, callback_data=f"ans_{o}_{GAMES_DATA.index(quiz)}"))
    await message.answer(f"❓ {quiz['q']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("ans_"))
async def check(callback: types.CallbackQuery):
    ans, idx = callback.data.split("_")[1], int(callback.data.split("_")[2])
    u_id = callback.from_user.id
    if ans == GAMES_DATA[idx]["a"]:
        users_db[u_id]["balance"] += 200
        await callback.message.edit_text(f"✅ To'g'ri! +200 so'm. Joriy balans: {users_db[u_id]['balance']} so'm")
    else:
        await callback.message.edit_text("❌ Noto'g'ri!")
    await callback.answer()

# --- 3. MARKET ---
@dp.message(F.text == "👨‍🏫 O'qituvchilar bo'limi")
async def market(message: types.Message):
    builder = InlineKeyboardBuilder()
    for k, v in PREMIUM_MATERIALS.items():
        builder.row(types.InlineKeyboardButton(text=f"{v['name']} ({v['price']} so'm)", callback_data=f"buy_{k}"))
    await message.answer("💎 *O'qituvchilar uchun pullik materiallar:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def buy(callback: types.CallbackQuery):
    item = PREMIUM_MATERIALS[callback.data.split("_")[1]]
    u_id = callback.from_user.id
    if users_db.get(u_id, {"balance": 0})["balance"] >= item["price"]:
        users_db[u_id]["balance"] -= item["price"]
        await callback.message.edit_text(f"✅ Sotib olindi: {item['name']}\n🔗 [Yuklab olish]({item['link']})", parse_mode="Markdown")
    else:
        await callback.message.answer("❌ Mablag' yetarli emas!")
    await callback.answer()

# --- 4. PROFIL (WALLET + REFERRAL + AI) ---
@dp.message(F.text == "👤 Mening profilim")
async def profile(message: types.Message):
    u = users_db.get(message.from_user.id, {"balance": 0})
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    text = (
        f"👤 *Foydalanuvchi:* @{message.from_user.username or 'Do`st'}\n"
        f"💰 *Balans:* `{u['balance']} so'm`\n\n"
        f"🔗 *Taklif havolasi:* \n`{link}`\n\n"
        "🤖 *AI Yordam:* Shunchaki xabar yozing..."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message()
async def ai_chat(message: types.Message):
    if message.text and not message.text.startswith("/"):
        await message.answer(f"🤖 *AI:* Savolingiz qabul qilindi. Sizga '{message.text}' bo'yicha ma'lumot qidiryapman...")

# --- RENDER SERVER & KEEP ALIVE ---
class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

def run_web(): HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), H).serve_forever()

def self_ping():
    import time
    while True:
        try:
            if RENDER_URL: urlopen(Request(RENDER_URL, headers={'User-Agent': 'Mozilla/5.0'}), timeout=10)
        except: pass
        time.sleep(240)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    asyncio.run(main())
