import asyncio
import os
import logging
import threading
import aiosqlite
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# --- SOZLAMALAR ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

# Render'da ma'lumotlar bazasi yo'lini to'g'irlash
DB_PATH = os.path.join(os.getcwd(), "users.db")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                referrer_id INTEGER,
                is_vip BOOLEAN DEFAULT 0,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# --- KLAVIATURALAR ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🤖 AI Kelajak Sherigi"), types.KeyboardButton(text="🧠 Bilim Sinash"))
    builder.row(types.KeyboardButton(text="👫 Do'stlarni taklif qilish"), types.KeyboardButton(text="💰 Mening Hamyonim"))
    builder.row(types.KeyboardButton(text="💎 VIP Bo'lim"), types.KeyboardButton(text="📞 Bog'lanish"))
    return builder.as_markup(resize_keyboard=True)

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "foydalanuvchi"
    
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not await cursor.fetchone():
                await db.execute("INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", 
                                 (user_id, username, referrer_id))
                if referrer_id:
                    await db.execute("UPDATE users SET balance = balance + 500 WHERE user_id = ?", (referrer_id,))
                    try:
                        await bot.send_message(referrer_id, f"🎉 Tabriklaymiz! Dostingiz @{username} taklifingiz bilan kirdi. Sizga 500 so'm bonus berildi!")
                    except: pass
                await db.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")

    welcome_text = (
        f"🌟 *Assalomu Alaykum, @{username}!*\n\n"
        "Siz O'zbekistondagi eng zamonaviy va aqlli *AI Bot* platformasiga xush kelibsiz!\n\n"
        "🚀 *Keling, kelajakni birga quramiz!*"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu())

@dp.message(F.text == "💰 Mening Hamyonim")
async def wallet(message: types.Message):
    balance = 0
    vip_status = "❌ Aktiv emas"
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT balance, is_vip FROM users WHERE user_id = ?", (message.from_user.id,))
            row = await cursor.fetchone()
            if row:
                balance, is_vip = row
                vip_status = "✅ Aktiv" if is_vip else "❌ Aktiv emas"
    except: pass

    text = (
        "🏦 *Sizning Shaxsiy Kabinetingiz*\n\n"
        f"💵 *ID:* `{message.from_user.id}`\n"
        f"💰 *Joriy Balans:* `{balance} so'm`\n"
        f"🏆 *VIP Status:* {vip_status}\n\n"
        "💡 *Passiv daromad:* Har bir taklif qilgan do'stingiz uchun sizga *500 so'm* avtomatik tushadi!"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "👫 Do'stlarni taklif qilish")
async def invite(message: types.Message):
    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(f"🔗 *Taklif havolangiz:*\n\n{invite_link}", parse_mode="Markdown")

@dp.message(F.text == "🤖 AI Kelajak Sherigi")
async def ai_handler(message: types.Message):
    await message.answer("🤖 *Sun'iy intellekt rejimi yoqildi!*\n\nSavolingizni yozing...")

# --- RENDER KEEP-ALIVE ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

def run_web():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), Handler).serve_forever()

def keep_alive_ping():
    import time
    while True:
        try:
            if RENDER_URL: urlopen(RENDER_URL, timeout=10)
        except: pass
        time.sleep(780)

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    asyncio.run(main())
