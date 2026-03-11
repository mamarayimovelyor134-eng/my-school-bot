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

# --- MEMORY DATABASE (For stability on Render Free) ---
# Note: Data resets on deploy, but ensures 100% uptime for now
users_db = {} 

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
    
    # Save user to memory
    if user_id not in users_db:
        users_db[user_id] = {"balance": 0, "username": username, "vip": False}
        
    # Check referral
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id in users_db and ref_id != user_id:
            users_db[ref_id]["balance"] += 500
            try:
                await bot.send_message(ref_id, f"🎉 Tabriklaymiz! @{username} taklifingiz bilan kirdi. +500 so'm!")
            except: pass

    welcome = (
        f"🌟 *Assalomu Alaykum, @{username}!*\n\n"
        "Siz O'zbekistondagi eng zamonaviy botga xush kelibsiz!\n\n"
        "🚀 *Menyudan kerakli bo'limni tanlang:*"
    )
    await message.answer(welcome, parse_mode="Markdown", reply_markup=main_menu())

@dp.message(F.text == "💰 Mening Hamyonim")
async def wallet(message: types.Message):
    u = users_db.get(message.from_user.id, {"balance": 0, "vip": False})
    text = (
        "🏦 *Sizning Kabinetingiz*\n\n"
        f"💰 *Balans:* `{u['balance']} so'm`\n"
        f"🏆 *VIP:* {'✅' if u['vip'] else '❌'}"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "👫 Do'stlarni taklif qilish")
async def invite(message: types.Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.answer(f"🔗 *Taklif havolangiz:*\n\n{link}\n\nDo'stingiz kirsa 500 so'm olasiz!", parse_mode="Markdown")

@dp.message(F.text == "🤖 AI Kelajak Sherigi")
async def ai_mode(message: types.Message):
    await message.answer("🤖 *Sun'iy intellekt tayyor!*\n\nSavolingizni yuboring...")

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
    logging.info("Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    asyncio.run(main())
