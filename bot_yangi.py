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
PAYMENT_PROVIDER_TOKEN = "399304918:TEST:92243" # TEST TOKEN (Click/Payme)
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- XOTIRA (DATABASE) ---
users_db = {} # {user_id: {"balance": 1000, "username": "name", "vip": False}}

# --- MA'LUMOTLAR ---
BOOKS_DATA = {
    "1-sinf": {"Matematika": "https://eduportal.uz/library/book/1", "Alifbe": "https://eduportal.uz/library/book/2"},
    "5-sinf": {"Tarix": "https://eduportal.uz/library/book/50", "Ingliz tili": "https://eduportal.uz/library/book/55"},
    "10-sinf": {"Fizika": "https://eduportal.uz/library/book/100", "Kimyo": "https://eduportal.uz/library/book/110"},
}

PREMIUM_MATERIALS = {
    "math_pro": {"name": "📐 Matematika: 7-sinf 'Funksiyalar' ochiq dars", "price": 5000, "link": "https://prezi.com/math-open-lesson"},
    "phys_pro": {"name": "🧲 Fizika: 9-sinf 'Magnit maydoni' slayd", "price": 7000, "link": "https://slideshare.com/physics-9"},
    "eng_pro": {"name": "🇬🇧 English: Grade 5 'My Family' lesson", "price": 4000, "link": "https://google.com/drive/eng-5"}
}

GAMES_DATA = {
    "math": [
        {"q": "12 * 5 + 15 = ?", "a": "75", "o": ["65", "75", "85", "70"]},
        {"q": "250 / 5 - 10 = ?", "a": "40", "o": ["30", "40", "50", "45"]}
    ],
    "logic": [
        {"q": "Qaysi oyda 28 kun bor?", "a": "Hamma oyda", "o": ["Fevral", "Yanvar", "Hamma oyda", "Hech qaysi"]},
        {"q": "Uni sotsang bo'lmaydi, uni sotib olib bo'lmaydi. Bu nima?", "a": "Aql", "o": ["Oltin", "Bilim", "Aql", "Kitob"]}
    ]
}

# --- KEYBOARDS ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📚 Maktab Darsliklari"))
    builder.row(types.KeyboardButton(text="👨‍🏫 O'qituvchilar Market (Pullik)"))
    builder.row(types.KeyboardButton(text="🎮 Interaktiv O'yinlar"), types.KeyboardButton(text="🤖 AI Assistant"))
    builder.row(types.KeyboardButton(text="💰 Balans to'ldirish"), types.KeyboardButton(text="💳 Hamyon"))
    builder.row(types.KeyboardButton(text="👫 Do'stlarni taklif qilish"))
    return builder.as_markup(resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        users_db[user_id] = {"balance": 1000, "username": message.from_user.username}
    
    # Referral check
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id in users_db and ref_id != user_id:
            users_db[ref_id]["balance"] += 500
            try: await bot.send_message(ref_id, f"🎉 Do'stingiz qo'shildi! +500 so'm!")
            except: pass

    await message.answer(
        f"🌟 *Assalomu Alaykum!* \n\n"
        "Siz O'zbekistondagi eng zamonaviy ta'lim platformasiga xush kelibsiz!\n\n"
        "🚀 *Kerakli bo'limni tanlang:*", 
        parse_mode="Markdown", reply_markup=main_menu()
    )

# --- DARSLIKLAR ---
@dp.message(F.text == "📚 Maktab Darsliklari")
async def show_grades(message: types.Message):
    builder = InlineKeyboardBuilder()
    for i in range(1, 12):
        builder.add(types.InlineKeyboardButton(text=f"{i}-sinf", callback_data=f"gr_{i}"))
    builder.adjust(3)
    await message.answer("📁 *Sinfingizni tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("gr_"))
async def show_grade_books(callback: types.CallbackQuery):
    grade = f"{callback.data.split('_')[1]}-sinf"
    books = BOOKS_DATA.get(grade, {"Matematika": "#", "Ona tili": "#"})
    builder = InlineKeyboardBuilder()
    for name, link in books.items():
        builder.row(types.InlineKeyboardButton(text=f"📖 {name}", url=link if link != "#" else "https://eduportal.uz"))
    await callback.message.edit_text(f"📚 *{grade} darsliklari:*", parse_mode="Markdown", reply_markup=builder.as_markup())

# --- MARKET ---
@dp.message(F.text == "👨‍🏫 O'qituvchilar Market (Pullik)")
async def school_market(message: types.Message):
    builder = InlineKeyboardBuilder()
    for k, v in PREMIUM_MATERIALS.items():
        builder.row(types.InlineKeyboardButton(text=f"{v['name']} ({v['price']} so'm)", callback_data=f"buy_{k}"))
    await message.answer("🛒 *Market:* Materialni tanlang va yuklab oling:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def process_purchase(callback: types.CallbackQuery):
    key = callback.data.split("_")[1]
    item = PREMIUM_MATERIALS[key]
    u_id = callback.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 0}
    
    if users_db[u_id]["balance"] >= item["price"]:
        users_db[u_id]["balance"] -= item["price"]
        await callback.message.edit_text(f"✅ *Sotib olindi:* {item['name']}\n🔗 [Havlola]({item['link']})", parse_mode="Markdown")
    else:
        await callback.message.answer(f"❌ Balans yetarli emas ({users_db[u_id]['balance']} so'm). Hamyonni to'ldiring.")
    await callback.answer()

# --- O'YINLAR ---
@dp.message(F.text == "🎮 Interaktiv O'yinlar")
async def choose_game(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔢 Matematika", callback_data="g_math"))
    builder.row(types.InlineKeyboardButton(text="🧩 Mantiq", callback_data="g_logic"))
    await message.answer("🎮 *O'yin turini tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("g_"))
async def play_game(callback: types.CallbackQuery):
    gtype = callback.data.split("_")[1]
    quiz = random.choice(GAMES_DATA[gtype])
    builder = InlineKeyboardBuilder()
    opts = quiz["o"]
    random.shuffle(opts)
    for o in opts:
        builder.add(types.InlineKeyboardButton(text=o, callback_data=f"check_{o}_{gtype}"))
    builder.adjust(2)
    await callback.message.edit_text(f"🕹 *Savol:* {quiz['q']}", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("check_"))
async def check_ans(callback: types.CallbackQuery):
    ans, gtype = callback.data.split("_")[1], callback.data.split("_")[2]
    correct = ""
    for q in GAMES_DATA[gtype]:
        if q["a"] == ans: correct = ans; break
    
    u_id = callback.from_user.id
    if ans == correct:
        users_db[u_id]["balance"] += 200
        await callback.message.edit_text(f"🏆 *To'g'ri!* +200 so'm balansga.")
    else:
        await callback.message.edit_text("❌ Noto'g'ri. Yana urinib ko'ring!")
    await callback.answer()

# --- TO'LOV TIZIMI ---
@dp.message(F.text == "💰 Balans to'ldirish")
async def topup(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💵 5,000 so'm", callback_data="pay_5000"))
    builder.row(types.InlineKeyboardButton(text="💵 10,000 so'm", callback_data="pay_10000"))
    await message.answer("💳 *To'lov miqdorini tanlang:*", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("pay_"))
async def send_pay(callback: types.CallbackQuery):
    amount = int(callback.data.split("_")[1])
    await bot.send_invoice(
        callback.from_user.id, "Balansni to'ldirish", f"{amount} so'm", "refill", 
        PAYMENT_PROVIDER_TOKEN, "UZS", [LabeledPrice(label="To'ldirish", amount=amount * 100)]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_check(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def success_pay(message: types.Message):
    summa = message.successful_payment.total_amount // 100
    users_db[message.from_user.id]["balance"] += summa
    await message.answer(f"✅ Balans `{summa}` so'mga to'ldirildi!")

# --- HAMYON ---
@dp.message(F.text == "💳 Hamyon")
async def show_wallet(message: types.Message):
    u = users_db.get(message.from_user.id, {"balance": 0})
    await message.answer(f"💰 *Sizning balansingiz:* `{u['balance']} so'm`", parse_mode="Markdown")

@dp.message(F.text == "👫 Do'stlarni taklif qilish")
async def invite(message: types.Message):
    me = await bot.get_me()
    await message.answer(f"🔗 *Taklif havolangiz:* \nhttps://t.me/{me.username}?start={message.from_user.id}")

@dp.message(F.text == "🤖 AI Assistant")
async def ai_mode(message: types.Message):
    await message.answer("🤖 *Sun'iy intellekt rejimi:* Savolingizni yozing...")

# --- RENDER SERVER & KEEP ALIVE ---
class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"ALIVE")
    def log_message(self, *a): pass

def run_web():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), H).serve_forever()

def self_ping():
    import time
    while True:
        try:
            if RENDER_URL:
                urlopen(Request(RENDER_URL, headers={'User-Agent': 'Mozilla/5.0'}), timeout=10)
        except: pass
        time.sleep(240)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    asyncio.run(main())
