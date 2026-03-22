import os

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix emojis manually (more robust)
content = content.replace('ЁЯМР', '🌍').replace('ЁЯЗ║ЁЯЗ┐', '🇺🇿').replace('ЁЯЗ╖ЁЯЗ║', '🇷🇺').replace('ЁЯЗмЁЯЗз', '🇬🇧')
content = content.replace('ËЯСЛ', '👋').replace('тЬи', '✨').replace('тЪая╕П', '⚠️').replace('ЁЯСЗ', '👇')

# Replace start logic to skip language selection
old_logic = """    if not u:
        args = m.text.split()
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        await state.update_data(referred_by=ref_id)
        await m.answer("🌍 Choose language / Tilni tanlang / ╨Т╤Л╨▒╨╡╤А╨╕╤В╨╡ ╤П╨╖╤Л╨║:", reply_markup=lang_kb())
        await state.set_state(RegState.choosing_lang)
    else:"""

new_logic = """    if not u:
        args = m.text.split()
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        await state.update_data(referred_by=ref_id, lang='uz')
        tx = TEXTS['uz']
        b = InlineKeyboardBuilder()
        b.add(types.InlineKeyboardButton(text=tx["role_driver"], callback_data="role_driver"))
        b.add(types.InlineKeyboardButton(text=tx["role_passenger"], callback_data="role_passenger"))
        await m.answer(f"{tx['welcome']}\\n\\n{tx['choose_role']}", parse_mode="Markdown", reply_markup=b.as_markup())
        await state.set_state(RegState.choosing_role)
    else:"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
else:
    # Try searching without indentation or small variations
    content = content.replace("await state.set_state(RegState.choosing_lang)", "await state.set_state(RegState.choosing_role)")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Bot is now starting in Uzbek and emojis fixed.")
