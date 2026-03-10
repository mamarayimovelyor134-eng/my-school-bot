import asyncio
from aiogram import Bot, Dispatcher, types, F

# BotFatherdan hozirgina olgan YANGI tokeningizni shu yerga qo'ying
TOKEN = "8213419235:AAH-ijI9gR51St5RCtOVVW5gsotB8NETeEg"

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

async def main():
    print("--- BOT TEST UCHUN TAYYOR ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
