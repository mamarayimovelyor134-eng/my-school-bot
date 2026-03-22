import os
import re

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Clean up the messy insertion in start_cmd
# We remove the improperly placed become_driver and fix the dangling else
# The pattern looks for the broken become_driver inside start_cmd
messy_pattern = r'await state\.set_state\(RegState\.choosing_role\)\s+@dp\.message\(F\.text == \"🚖 Haydovchi bo\'lib ishlash\"\)\s+async def become_driver\(.*?\)\s+await state\.set_state\(RegState\.entering_car\)'
fixed_insertion = r'await state.set_state(RegState.choosing_role)'

content = re.sub(messy_pattern, fixed_insertion, content, flags=re.DOTALL)

# 2. Add become_driver properly AFTER the whole start_cmd function finishes
new_handler = r'''
@dp.message(F.text == "🚖 Haydovchi bo'lib ishlash")
async def become_driver(m: types.Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    u = await get_user_db(m.from_user.id)
    await state.update_data(role='driver', lang=lang, full_name=u[2])
    await m.answer(TEXTS[lang]["enter_car"])
    await state.set_state(RegState.entering_car)
'''

# Find the end of start_cmd else block (mkb(m.from_user.id)))
end_of_start = r'await m\.answer\(t\(u\[6\], \"welcome\"\), parse_mode=\"Markdown\", reply_markup=await mkb\(m\.from_user\.id\)\)'

if re.search(end_of_start, content):
    content = re.sub(end_of_start, end_of_start + "\n" + new_handler, content)
else:
    # Fallback
    content += "\n" + new_handler

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: become_driver handler moved outside start_cmd properly.")
