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

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MEMORY DATABASE ---
users_db = {} 

# --- TESTLAR (SAVOLLAR TO'PLAMI) ---
QUIZ_DATA = [
    {
        "question": "📝 'Xamsa' asari necha dostonni o'z ichiga oladi?",
        "options": ["3 ta", "4 ta", "5 ta", "7 ta"],
        "correct": "5 ta"
    },
    {
        "question": "🔢 15 x 6 + 10 amalini bajaring:",
        "options": ["90", "100", "110", "80"],
        "correct": "100"
    },
    {
        "question": "🌍 O'zbekiston mustaqilligi qachon e'lon qilingan?",
        "options": ["1990", "1991", "1992", "1989"],
        "correct": "1991"
    }
]

# --- KEYBOARDS ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🤖 AI Kelajak Sherigi"), types.KeyboardButton(text="🧠 Bilim Sinash"))
    builder.row(types.KeyboardButton(text="👫 Do'stlarni taklif qilish"), types.KeyboardButton(text="💰 Mening Hamyonim"))
    builder.row(types.KeyboardButton(text="💎 VIP Bo'lim"), types.KeyboardButton(text="📞 Bog'lanish"))
    return builder.as_markup(resize_keyboard=True)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "foydalanuvchi"
    if user_id not in users_db:
        users_db[user_id] = {"balance": 0, "username": username, "vip": False}
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id in users_db and ref_id != user_id:
            users_db[ref_id]["balance"] += 500
            try: await bot.send_message(ref_id, f"🎉 Do'stingiz qo'shildi! +500 so'm!")
            except: pass

    await message.answer(f"🌟 *Assalomu Alaykum!* Siz aqlli tizimdasiz.", parse_mode="Markdown", reply_markup=main_menu())

# --- BILIM SINASH (TEST TIZIMI) ---
@dp.message(F.text == "🧠 Bilim Sinash")
async def start_quiz(message: types.Message):
    quiz = random.choice(QUIZ_DATA)
    builder = InlineKeyboardBuilder()
    for option in quiz["options"]:
        # Callback data ichida savol indexi va javobni saqlaymiz
        builder.row(types.InlineKeyboardButton(text=option, callback_data=f"ans_{option}_{QUIZ_DATA.index(quiz)}"))
    
    await message.answer(f"🚀 *DIQQAT SAVOL:*\n\n{quiz['question']}", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("ans_"))
async def handle_answer(callback: types.CallbackQuery):
    data = callback.data.split("_")
    user_answer = data[1]
    quiz_idx = int(data[2])
    quiz = QUIZ_DATA[quiz_idx]
    
    user_id = callback.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 0, "vip": False}

    if user_answer == quiz["correct"]:
        users_db[user_id]["balance"] += 100 # To'g'ri javob uchun 100 so'm
        await callback.message.edit_text(f"✅ *BARAKALLA!* To'g'ri topdingiz.\n💰 Sizga *100 so'm* bonus berildi!\n\nJoriy balans: {users_db[user_id]['balance']} so'm", parse_mode="Markdown")
    else:
        await callback.message.edit_text(f"❌ *XATO!* To'g'ri javob: *{quiz['correct']}* edi.\n\nYana urinib ko'ring!", parse_mode="Markdown")
    
    await callback.answer()

@dp.message(F.text == "💰 Mening Hamyonim")
async def wallet(message: types.Message):
    u = users_db.get(message.from_user.id, {"balance": 0, "vip": False})
    await message.answer(f"🏦 *Hamyon:* `{u['balance']} so'm`", parse_mode="Markdown")

@dp.message(F.text == "👫 Do'stlarni taklif qilish")
async def invite(message: types.Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.answer(f"🔗 *Taklif havolangiz:*\n\n{link}", parse_mode="Markdown")

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
