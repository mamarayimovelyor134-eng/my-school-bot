import os

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# The broken handler part that is too high up
broken_code = r'''
@dp.message(F.text == "🚖 Haydovchi bo'lib ishlash")
async def become_driver(m: types.Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    u = await get_user_db(m.from_user.id)
    await state.update_data(role='driver', lang=lang, full_name=u[2])
    await m.answer(TEXTS[lang]["enter_car"])
    await state.set_state(RegState.entering_car)
'''

# 1. Remove it from the top
content = content.replace(broken_code, '')

# 2. Insert it properly lower down, after dp definition
# Let's insert it after start_cmd function (approximately line 282 in original)
insertion_point = r'await state.set_state(RegState.choosing_role)'
if insertion_point in content:
    content = content.replace(insertion_point, insertion_point + "\n" + broken_code)
else:
    # Fallback: Just put it anywhere after dp = ...
    content = content.replace('dp = Dispatcher(storage=MemoryStorage())', 'dp = Dispatcher(storage=MemoryStorage())\n' + broken_code)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: become_driver handler moved after dp definition.")
