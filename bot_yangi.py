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

# --- O'YINLAR MA'LUMOTI ---
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

# --- MENU ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎮 Interaktiv O'yin-Darslar"))
    builder.row(types.KeyboardButton(text="📚 Maktab Darsliklari"), types.KeyboardButton(text="👨‍🏫 O'qituvchilar uchun"))
    builder.row(types.KeyboardButton(text="🧠 Bilim Sinash"), types.KeyboardButton(text="🤖 AI Assistant"))
    builder.row(types.KeyboardButton(text="💰 Hamyon"), types.KeyboardButton(text="👫 Do'stlarni taklif qilish"))
    return builder.as_markup(resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 0}
    await message.answer("🎓 *Milliy Ta'lim Platformasi 2.0!*\n\nDarslar endi yanada qiziqarli o'yinlar shaklida!", parse_mode="Markdown", reply_markup=main_menu())

# --- O'YINLAR BO'LIMI ---
@dp.message(F.text == "🎮 Interaktiv O'yin-Darslar")
async def show_games(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔢 Matematik Duel", callback_data="play_math"))
    builder.row(types.InlineKeyboardButton(text="🧩 Mantiqiy Kvest", callback_data="play_logic"))
    await message.answer("🎮 *O'yin turini tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("play_"))
async def start_game(callback: types.CallbackQuery):
    game_type = callback.data.split("_")[1]
    quiz = random.choice(GAMES_DATA[game_type])
    
    builder = InlineKeyboardBuilder()
    options = quiz["o"]
    random.shuffle(options)
    for opt in options:
        builder.add(types.InlineKeyboardButton(text=opt, callback_data=f"res_{opt}_{game_type}"))
    builder.adjust(2)
    
    await callback.message.edit_text(f"🕹 *Savol:* {quiz['q']}", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("res_"))
async def check_game(callback: types.CallbackQuery):
    data = callback.data.split("_")
    ans, g_type = data[1], data[2]
    
    # To'g'ri javobni topish
    correct_ans = ""
    for q in GAMES_DATA[g_type]:
        if q["a"] == ans or ans in q["o"]: # Soddalashtirilgan qidiruv
            correct_ans = q["a"]
            break

    user_id = callback.from_user.id
    if user_id not in users_db: users_db[user_id] = {"balance": 0}

    if ans == correct_ans:
        users_db[user_id]["balance"] += 200
        await callback.message.edit_text(f"🏆 *TABRIKLAYMIZ!* Siz yutdingiz!\n💰 +200 ball hamyoningizga qo'shildi.", parse_mode="Markdown")
    else:
        await callback.message.edit_text(f"💔 *YUTQAZDINGIZ!* To'g'ri javob: {correct_ans} edi.\n\nYana urinib ko'rasizmi?", parse_mode="Markdown")
    
    await callback.answer()

# --- QOLGAN BO'LIMLAR ---
@dp.message(F.text == "📚 Maktab Darsliklari")
async def books(message: types.Message):
    await message.answer("📚 Darsliklar bo'limi yangilanmoqda...")

@dp.message(F.text == "💰 Hamyon")
async def wallet(message: types.Message):
    u = users_db.get(message.from_user.id, {"balance": 0})
    await message.answer(f"💰 *Balans:* `{u['balance']} ball`", parse_mode="Markdown")

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
