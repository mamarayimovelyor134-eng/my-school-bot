import asyncio
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types, F

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(F.text == "/start")
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="🧠 Testni boshlash")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Salom! Testni boshlang:", reply_markup=keyboard)


@dp.message(F.text == "🧠 Testni boshlash")
async def start_test(message: types.Message):
    buttons = [
        [types.InlineKeyboardButton(text="Alisher Navoiy", callback_data="ok")],
        [types.InlineKeyboardButton(text="Jules Verne", callback_data="no")]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("❓ 'Xamsa' muallifi kim?", reply_markup=keyboard)


@dp.callback_query()
async def callbacks(callback: types.CallbackQuery):
    if callback.data == "ok":
        await callback.message.answer("✅ BARAKALLA! To'g'ri.")
    else:
        await callback.message.answer("❌ Noto'g'ri.")
    await callback.answer()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *a): pass


def web():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    threading.Thread(target=web, daemon=True).start()
    asyncio.run(main())
