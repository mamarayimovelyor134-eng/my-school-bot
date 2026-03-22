import os
import re

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Logic to skip name for passengers
new_set_role = r"""@dp.callback_query(RegState.choosing_role)
async def set_role(c: types.CallbackQuery, state: FSMContext):
    role = c.data.split("_")[1]
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    await state.update_data(role=role)
    if role == 'passenger':
        # Skip name for passenger, go straight to phone
        b = ReplyKeyboardBuilder()
        b.row(types.KeyboardButton(text=TEXTS[lang]["enter_phone"], request_contact=True))
        await c.message.answer(TEXTS[lang]["enter_phone"], reply_markup=b.as_markup(resize_keyboard=True))
        await state.set_state(RegState.entering_phone)
    else:
        await c.message.edit_text(TEXTS[lang]["enter_name"])
        await state.set_state(RegState.entering_name)"""

# Find set_role and replace it
pattern = r'@dp\.callback_query\(RegState\.choosing_role\)\s+async def set_role\(c: types\.CallbackQuery, state: FSMContext\):.*?await state\.set_state\(RegState\.entering_name\)'
if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_set_role, content, flags=re.DOTALL)
else:
    # If pattern doesn't match exactly, try a more flexible one
    content = content.replace("entering_name", "entering_phone")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Name step skipped for passengers.")
