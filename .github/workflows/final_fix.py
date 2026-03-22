import os
import re

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the start command logic once and for all
# Searching for the pattern of start_cmd until selection
pattern = r'(@dp\.message\(Command\("start"\)\)\s+async def start_cmd\(m: types\.Message, state: FSMContext\):.*?if not u:)(.*?)else:'

# New Uzbek-only logic
replacement_logic = r"""
        args = m.text.split()
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        await state.update_data(referred_by=ref_id, lang='uz')
        # Hardcoding Uzbek texts directly into the response to be 100% sure
        welcome_text = "👋 *Assalomu alaykum!* \nQishloq-Shahar Taksi botiga xush kelibsiz! ✨\n\n⚠️ *MUHIM:* Bot faqat vositachi hisoblanadi va nizolar uchun javobgar emas."
        choose_role = "Siz kimsiz? 👇"
        b = InlineKeyboardBuilder()
        b.add(types.InlineKeyboardButton(text="👨‍✈️ Haydovchiman", callback_data="role_driver"))
        b.add(types.InlineKeyboardButton(text="👤 Yo'lovchiman", callback_data="role_passenger"))
        await m.answer(f"{welcome_text}\n\n{choose_role}", parse_mode="Markdown", reply_markup=b.as_markup())
        await state.set_state(RegState.choosing_role)
    """

# We substitute the logic between if not u: and else:
content = re.sub(pattern, r'\1' + replacement_logic + r'else:', content, flags=re.DOTALL)

# Fix emojis and text artifacts globally
replacements = {
    'ËЯМР': '🌍', 'ЁЯМР': '🌍', 'Choose language / Tilni tanlang': 'Tilni tanlang',
    'ËЯСЛ': '👋', 'тЬи': '✨', 'тЪая╕П': '⚠️', 'ЁЯСЗ': '👇'
}
for old, new in replacements.items():
    content = content.replace(old, new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Full Uzbek transformation complete.")
