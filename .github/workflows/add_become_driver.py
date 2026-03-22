import os
import re

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    orig_content = f.read()

# 1. Update mkb function to include "Become Driver" button for passengers
new_mkb = r"""async def mkb(uid):
    lang = await get_lang(uid)
    u = await get_user_db(uid)
    tx = TEXTS[lang]
    b = ReplyKeyboardBuilder()
    if u and u[4] == "driver":
        # Driver Menu
        b.row(types.KeyboardButton(text=tx["main_driver"]), types.KeyboardButton(text=tx["main_order"]))
        b.row(types.KeyboardButton(text=tx["main_search"]), types.KeyboardButton(text=tx["main_profile"]))
        b.row(types.KeyboardButton(text=tx["main_balance"]), types.KeyboardButton(text=tx["main_sos"]))
    else:
        # Passenger Menu (Enhanced)
        b.row(types.KeyboardButton(text=tx["main_order"]), types.KeyboardButton(text=tx["main_search"]))
        b.row(types.KeyboardButton(text=tx["main_profile"]), types.KeyboardButton(text=tx["main_sos"]))
        b.row(types.KeyboardButton(text="🚖 Haydovchi bo'lib ishlash"))
    b.row(types.KeyboardButton(text=tx["main_support"]))
    return b.as_markup(resize_keyboard=True)"""

# 2. Add handler for "Become Driver" button
become_driver_handler = r"""
@dp.message(F.text == "🚖 Haydovchi bo'lib ishlash")
async def become_driver(m: types.Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    u = await get_user_db(m.from_user.id)
    await state.update_data(role='driver', lang=lang, full_name=u[2])
    await m.answer(TEXTS[lang]["enter_car"])
    await state.set_state(RegState.entering_car)
"""

# Replace mkb function
pattern_mkb = r'async def mkb\(uid\):.*?return b\.as_markup\(resize_keyboard=True\)'
content = re.sub(pattern_mkb, new_mkb, orig_content, flags=re.DOTALL)

# Insert the handler before searching handler or at the end
content = content.replace('# --- BOT HANDLERS ---', '# --- BOT HANDLERS ---\n' + become_driver_handler)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Become Driver functionality added for passengers.")
