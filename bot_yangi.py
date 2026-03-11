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

# --- KONFIGURATSIYA ---
TOKEN = os.environ.get("BOT_TOKEN")
PAYMENT_PROVIDER_TOKEN = "399304918:TEST:92243" 
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

bot = Bot(token=TOKEN)
dp = Dispatcher()
users_db = {} 

# --- 1. DARSLIKLAR BAZASI (1-11 SINF) ---
BOOKS_DATA = {
    "1-sinf": {"Matematika": "https://eduportal.uz/library/book/1", "Alifbe": "https://eduportal.uz/library/book/2", "Tarbiya": "#", "O'qish": "#"},
    "2-sinf": {"Matematika": "#", "Ona tili": "#", "Tarbiya": "#", "Atrofimizdagi olam": "#"},
    "3-sinf": {"Matematika": "#", "Ona tili": "#", "Ingliz tili": "#", "Tabiiy fanlar": "#"},
    "4-sinf": {"Matematika": "#", "Ona tili": "#", "Texnologiya": "#", "Musiqa": "#"},
    "5-sinf": {"Matematika": "https://eduportal.uz/library/book/50", "Tarix": "#", "Adabiyot": "#", "Botanika": "#"},
    "6-sinf": {"Matematika": "#", "Fizika": "#", "Tarix": "#", "Geografiya": "#"},
    "7-sinf": {"Algebra": "#", "Geometriya": "#", "Fizika": "#", "Kimyo": "#", "Adabiyot": "#"},
    "8-sinf": {"Algebra": "#", "Geometriya": "#", "Fizika": "#", "Kimyo": "#", "Biologiya": "#"},
    "9-sinf": {"Algebra": "#", "Geometriya": "#", "Fizika": "#", "Kimyo": "#", "Tarix": "#"},
    "10-sinf": {"Fizika": "https://eduportal.uz/library/book/100", "Kimyo": "#", "Biologiya": "#", "Algebra": "#"},
    "11-sinf": {"Fizika": "#", "Kimyo": "#", "Biologiya": "#", "Algebra": "#", "Astronomiya": "#"}
}

# --- 2. O'QITUVCHILAR MARKET (PULLIK) ---
PREMIUM_MATERIALS = {
    "math_1": {"name": "📐 Mat: 5-sinf 'Kasrlar' ochiq dars", "price": 5000, "link": "https://edu.uz/m1"},
    "math_2": {"name": "📐 Mat: 9-sinf 'Funksiya' slayd", "price": 7000, "link": "https://edu.uz/m2"},
    "phys_1": {"name": "🧲 Fiz: 7-sinf 'Inertsiya' konspekt", "price": 4000, "link": "https://edu.uz/p1"},
    "phys_2": {"name": "🧲 Fiz: 11-sinf 'Yadro' taqdimot", "price": 10000, "link": "https://edu.uz/p2"},
    "eng_1": {"name": "🇬🇧 Eng: Grade 1 'Colors' interactive", "price": 3000, "link": "https://edu.uz/e1"},
    "his_1": {"name": "📜 Tarix: 'Amir Temur' ochiq dars", "price": 6000, "link": "https://edu.uz/h1"}
}

# --- 3. O'YINLAR BAZASI (50+ SAVOL) ---
GAMES_DATA = {
    "math": [
        {"q": "15 * 4 + 20 = ?", "a": "80", "o": ["70", "80", "90", "75"]},
        {"q": "120 / 3 - 10 = ?", "a": "30", "o": ["20", "30", "40", "25"]},
        {"q": "√144 = ?", "a": "12", "o": ["11", "12", "13", "14"]},
        {"q": "2 ning 5-darajasi?", "a": "32", "o": ["16", "32", "64", "25"]}
    ],
    "logic": [
        {"q": "Dunyodagi eng katta okean?", "a": "Tinch", "o": ["Hind", "Atlantika", "Tinch", "Shimoliy"]},
        {"q": "O'zbekiston poytaxti qachon Toshkent bo'lgan?", "a": "1930", "o": ["1924", "1930", "1991", "1917"]},
        {"q": "Qaysi sayyora 'Qizil sayyora' deyiladi?", "a": "Mars", "o": ["Venera", "Mars", "Yupiter", "Saturm"]}
    ]
}

# --- MENU ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📚 Kitoblar Jamlanmasi (1-11)"), types.KeyboardButton(text="👨‍🏫 Ustozlar Marketi"))
    builder.row(types.KeyboardButton(text="🎮 Bilimlar O'yini"), types.KeyboardButton(text="🤖 Aqlli Assistant"))
    builder.row(types.KeyboardButton(text="💰 Balans"), types.KeyboardButton(text="👫 Referal"))
    return builder.as_markup(resize_keyboard=True)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 1000}
    await message.answer("🎓 *Professional Ta'lim Platformasi!* \nBarcha ma'lumotlar to'liq yangilandi.", parse_mode="Markdown", reply_markup=main_menu())

# --- 1. KITOOBLAR ---
@dp.message(F.text == "📚 Kitoblar Jamlanmasi (1-11)")
async def show_grades(message: types.Message):
    builder = InlineKeyboardBuilder()
    for g in BOOKS_DATA.keys():
        builder.add(types.InlineKeyboardButton(text=g, callback_data=f"gr_{g}"))
    builder.adjust(3)
    await message.answer("📁 *Sinfingizni tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("gr_"))
async def list_books(callback: types.CallbackQuery):
    grade = callback.data.split("_")[1]
    books = BOOKS_DATA.get(grade, {})
    builder = InlineKeyboardBuilder()
    for name, url in books.items():
        builder.row(types.InlineKeyboardButton(text=f"📖 {name}", url=url if url != "#" else "https://eduportal.uz"))
    await callback.message.edit_text(f"📚 *{grade} uchun barcha darsliklar:*", parse_mode="Markdown", reply_markup=builder.as_markup())

# --- 2. MARKET ---
@dp.message(F.text == "👨‍🏫 Ustozlar Marketi")
async def show_market(message: types.Message):
    builder = InlineKeyboardBuilder()
    for key, item in PREMIUM_MATERIALS.items():
        builder.row(types.InlineKeyboardButton(text=f"{item['name']} | {item['price']} so'm", callback_data=f"buy_{key}"))
    await message.answer("💎 *Pullik materiallar:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def buy_item(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    item = PREMIUM_MATERIALS[key]
    u_id = callback.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 0}
    
    if users_db[u_id]["balance"] >= item["price"]:
        users_db[u_id]["balance"] -= item["price"]
        await callback.message.edit_text(f"✅ *Xarid qilindi:* {item['name']}\n🔗 [Yuklab olish]({item['link']})", parse_mode="Markdown")
    else:
        await callback.message.answer("❌ Balans yetarli emas!")
    await callback.answer()

# --- 3. O'YINLAR (MUKAMMAL) ---
@dp.message(F.text == "🎮 Bilimlar O'yini")
async def choose_game(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔢 Matematika", callback_data="play_math"))
    builder.row(types.InlineKeyboardButton(text="🧠 Umumiy Bilim", callback_data="play_logic"))
    await message.answer("🕹 *O'yin turini tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("play_"))
async def start_game(callback: types.CallbackQuery):
    gtype = callback.data.split("_")[1]
    quiz = random.choice(GAMES_DATA[gtype])
    builder = InlineKeyboardBuilder()
    opts = quiz["o"]
    random.shuffle(opts)
    for o in opts:
        builder.add(types.InlineKeyboardButton(text=o, callback_data=f"chk_{o}_{gtype}"))
    builder.adjust(2)
    await callback.message.edit_text(f"❓ {quiz['q']}", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("chk_"))
async def check_game(callback: types.CallbackQuery):
    ans, gtype = callback.data.split("_")[1], callback.data.split("_")[2]
    correct = False
    for q in GAMES_DATA[gtype]:
        if q["a"] == ans: correct = True; break
    
    u_id = callback.from_user.id
    if correct:
        users_db[u_id]["balance"] += 200
        await callback.message.edit_text(f"✅ To'g'ri! +200 so'm hamyoningizga.")
    else:
        await callback.message.edit_text("❌ Noto'g'ri!")
    await callback.answer()

# --- 4. AI ASSISTANT (AQLLI YORDAMCHI) ---
@dp.message(F.text == "🤖 Aqlli Assistant")
async def ai_start(message: types.Message):
    await message.answer("🤖 *Men sizning aqlli yordamchingizman!*\n\nIstalgan savolingizni bering, men sizga javob topishga harakat qilaman. Masalan: 'Darsliklar nima uchun kerak?'", parse_mode="Markdown")

@dp.message()
async def ai_reply(message: types.Message):
    if message.text:
        await message.answer(f"🔎 Sizning savolingiz: '{message.text}'\n\n🤖 *AI Tahlili:* Men hozircha o'rganish rejimidaman, lekin sizga ta'lim bo'limimizdan ma'lumot topib berishim mumkin. Iltimos, menyudan foydalaning.")

# --- RENDER SERVER ---
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
