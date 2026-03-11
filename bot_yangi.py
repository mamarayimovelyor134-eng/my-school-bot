import asyncio
import os
import logging
import threading
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F

# Logging
logging.basicConfig(level=logging.INFO)

# Token
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

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


def run_web_server():
    """Render portini ochiq ushlab turuvchi yordamchi server"""
    port = int(os.environ.get("PORT", 10000))

    async def handle(request):
        return web.Response(text="Bot is alive!")

    async def run():
        app = web.Application()
        app.router.add_get("/", handle)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logging.info(f"Web server {port} portda ishlamoqda")
        await asyncio.sleep(3600 * 24 * 365)  # 1 yil ushlab turadi

    asyncio.run(run())


async def main():
    logging.info("Bot polling ishga tushdi...")
    # Eski webhookni o'chirish
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Web serverni alohida threadda ishga tushiramiz
    t = threading.Thread(target=run_web_server, daemon=True)
    t.start()
    # Botni asosiy threadda ishga tushiramiz
    asyncio.run(main())
