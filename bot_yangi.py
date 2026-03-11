import asyncio
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Logging yoqish (Render loglarida xatolarni ko'rish uchun)
logging.basicConfig(level=logging.INFO)

# Token muhit o'zgaruvchisidan olinadi (Render Environment Variables)
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable topilmadi!")

# Render saytidagi loyihaning URL manzili
WEBHOOK_HOST = os.environ.get("RENDER_EXTERNAL_URL", "")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Port (Render o'zi beradi)
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(F.text == "/start")
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="🧠 Testni boshlash")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Salom! Bot ishga tushdi. Testni boshlang:", reply_markup=keyboard)


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


async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logging.info("Webhook o'chirildi.")


def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logging.info(f"Server {PORT} portda ishlamoqda...")
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
