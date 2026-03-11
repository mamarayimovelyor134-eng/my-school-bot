import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F

# BotFatherdan hozirgina olgan YANGI tokeningizni shu yerga qo'ying
# Xavfsizlik uchun token muhit o'zgaruvchilaridan (BOT_TOKEN) olinadi:
TOKEN = os.environ.get("BOT_TOKEN", "8213419235:AAH-ijI9gR51St5RCtOVVW5gsotB8NETeEg")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.text == "/start")
async def start(message: types.Message):
    kb = [[types.KeyboardButton(text="🧠 Testni boshlash")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Salom! Bot qayta tug'ildi. Testni boshlang:", reply_markup=keyboard)

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

async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    print("--- BOT TEST UCHUN TAYYOR ---")
    
    # Render xizmatida Port scan timeout xatosini oldini olish uchun yordamchi web server:
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server port {port} da ishga tushdi.")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
