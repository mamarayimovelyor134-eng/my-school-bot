import os

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.readlines()

# Totally rewrite the start_cmd section manually by line number or pattern
new_lines = []
skip = False
for line in content:
    if '@dp.message(Command("start"))' in line:
        new_lines.append('@dp.message(Command("start"))\n')
        new_lines.append('async def start_cmd(m: types.Message, state: FSMContext):\n')
        new_lines.append('    u = await get_user_db(m.from_user.id)\n')
        new_lines.append('    if not u:\n')
        new_lines.append('        args = m.text.split()\n')
        new_lines.append('        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None\n')
        new_lines.append("        await state.update_data(referred_by=ref_id, lang='uz')\n")
        new_lines.append('        welcome_text = "👋 *Assalomu alaykum!* \\nQishloq-Shahar Taksi botiga xush kelibsiz! ✨\\n\\n⚠️ *MUHIM:* Bot faqat vositachi hisoblanadi va nizolar uchun javobgar emas."\n')
        new_lines.append('        choose_role = "Siz kimsiz? 👇"\n')
        new_lines.append('        b = InlineKeyboardBuilder()\n')
        new_lines.append('        b.add(types.InlineKeyboardButton(text="👨‍✈️ Haydovchiman", callback_data="role_driver"))\n')
        new_lines.append('        b.add(types.InlineKeyboardButton(text="👤 Yo\'lovchiman", callback_data="role_passenger"))\n')
        new_lines.append('        await m.answer(f"{welcome_text}\\n\\n{choose_role}", parse_mode="Markdown", reply_markup=b.as_markup())\n')
        new_lines.append('        await state.set_state(RegState.choosing_role)\n')
        new_lines.append('    else:\n')
        skip = True
        continue
    
    if skip and 'async def' in line and 'start_cmd' not in line:
        skip = False
    
    if not skip:
        new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("SUCCESS: Start command totally rewritten and fixed.")
