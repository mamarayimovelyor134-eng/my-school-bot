import asyncio
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MEMORY DATABASE ---
users_db = {} 

# --- TA'LIM BAZASI (DARSLIKLAR VA MATERIALLAR) ---
# Namuna sifatida bir nechta ma'lumotlar. Siz bu yerga barcha PDF havolalarni qo'shishingiz mumkin.
BOOKS_DATA = {
    "1-sinf": {"Matematika": "https://eduportal.uz/library/book/1", "Alifbe": "https://eduportal.uz/library/book/2"},
    "5-sinf": {"Tarix": "https://eduportal.uz/library/book/50", "Ingliz tili": "https://eduportal.uz/library/book/55"},
    "10-sinf": {"Fizika": "https://eduportal.uz/library/book/100", "Kimyo": "https://eduportal.uz/library/book/110"},
}

# --- KEYBOARDS ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📚 Maktab Darsliklari"), types.KeyboardButton(text="👨‍🏫 O'qituvchilar uchun"))
    builder.row(types.KeyboardButton(text="🧠 Bilim Sinash"), types.KeyboardButton(text="🤖 AI Assistant"))
    builder.row(types.KeyboardButton(text="💰 Hamyon"), types.KeyboardButton(text="💎 VIP Bo'lim"))
    builder.row(types.KeyboardButton(text="👫 Do'stlarni taklif qilish"))
    return builder.as_markup(resize_keyboard=True)

def grades_keyboard():
    builder = InlineKeyboardBuilder()
    for grade in [f"{i}-sinf" for i in range(1, 12)]:
        builder.add(types.InlineKeyboardButton(text=grade, callback_data=f"grade_{grade}"))
    builder.adjust(3)
    return builder.as_markup()

# --- HANDLERS ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "foydalanuvchi"
    if user_id not in users_db:
        users_db[user_id] = {"balance": 0, "username": username, "vip": False}
    
    welcome = (
        f"👋 *Assalomu alaykum, @{username}!*\n\n"
        "🎓 *Milliy Ta'lim Platformasiga xush kelibsiz!*\n"
        "Bu yerda siz 1-11 sinf darsliklarini topishingiz va bilimingizni sinashingiz mumkin.\n\n"
        "🚀 *Kerakli bo'limni tanlang:*"
    )
    await message.answer(welcome, parse_mode="Markdown", reply_markup=main_menu())

# --- DARSLIKLAR BO'LIMI ---
@dp.message(F.text == "📚 Maktab Darsliklari")
async def show_grades(message: types.Message):
    await message.answer("📁 *O'zingiz o'qiydigan sinfni tanlang:*", parse_mode="Markdown", reply_markup=grades_keyboard())

@dp.callback_query(F.data.startswith("grade_"))
async def show_subjects(callback: types.CallbackQuery):
    grade = callback.data.split("_")[1]
    builder = InlineKeyboardBuilder()
    
    # Shu sinfga tegishli fanlarni chiqarish
    subjects = BOOKS_DATA.get(grade, {"Matematika": "#", "Ona tili": "#", "Tarix": "#"})
    for sub in subjects:
        builder.row(types.InlineKeyboardButton(text=f"📖 {sub}", url=subjects[sub] if subjects[sub] != "#" else "https://eduportal.uz"))
    
    await callback.message.edit_text(f"📚 *{grade} uchun darsliklar ro'yxati:*", parse_mode="Markdown", reply_markup=builder.as_markup())

# --- O'QITUVCHILAR BO'LIMI ---
@dp.message(F.text == "👨‍🏫 O'qituvchilar uchun")
async def teacher_corner(message: types.Message):
    await message.answer(
        "👨‍🏫 *O'qituvchilar burchagi*\n\n"
        "Bu yerda siz quyidagilarni topishingiz mumkin:\n"
        "🔹 Dars ishlanmalari (Konspektlar)\n"
        "🔹 Metodik qo'llanmalar\n"
        "🔹 Davlat ta'lim standartlari (DTS)\n\n"
        "_Hozirda materiallar yuklanmoqda..._",
        parse_mode="Markdown"
    )

# --- QOLGAN BO'LIMLAR (PLACEHOLDERS) ---
@dp.message(F.text == "💰 Hamyon")
async def wallet(message: types.Message):
    u = users_db.get(message.from_user.id, {"balance": 0})
    await message.answer(f"💰 *ID:* `{message.from_user.id}`\n🏦 *Balans:* `{u['balance']} so'm`", parse_mode="Markdown")

@dp.message(F.text == "👫 Do'stlarni taklif qilish")
async def invite(message: types.Message):
    me = await bot.get_me()
    await message.answer(f"🔗 *Taklif havolangiz:* \nhttps://t.me/{me.username}?start={message.from_user.id}", parse_mode="Markdown")

# --- RENDER WEB SERVER ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

def run_web():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

def keep_alive():
    import time
    while True:
        try:
            if RENDER_URL: urlopen(RENDER_URL, timeout=10)
        except: pass
        time.sleep(600)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    asyncio.run(main())
