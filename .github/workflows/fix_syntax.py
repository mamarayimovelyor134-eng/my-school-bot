import os

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken start_cmd with properly closed quotes and no line breaks within the string
import re
new_start_logic = r'''@dp.message(Command("start"))
async def start_cmd(m: types.Message, state: FSMContext):
    u = await get_user_db(m.from_user.id)
    if not u:
        args = m.text.split()
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        await state.update_data(referred_by=ref_id, lang='uz')
        welcome_text = "👋 *Assalomu alaykum!* \nQishloq-Shahar Taksi botiga xush kelibsiz! ✨\n\n⚠️ *MUHIM:* Bot faqat vositachi hisoblanadi va nizolar uchun javobgar emas."
        choose_role = "Siz kimsiz? 👇"
        b = InlineKeyboardBuilder()
        b.add(types.InlineKeyboardButton(text="👨‍✈️ Haydovchiman", callback_data="role_driver"))
        b.add(types.InlineKeyboardButton(text="👤 Yo'lovchiman", callback_data="role_passenger"))
        await m.answer(f"{welcome_text}\n\n{choose_role}", parse_mode="Markdown", reply_markup=b.as_markup())
        await state.set_state(RegState.choosing_role)
    else:'''

# Find the broken part and replace it
# The error was around: welcome_text = "\U0001f44b *Assalomu alaykum!* 
# So we look for any start_cmd and replace it with this clean one.
pattern = r'@dp\.message\(Command\(\"start\"\)\).*?if not u:.*?await state\.set_state\(RegState\.choosing_role\)\s+else:'
content = re.sub(pattern, new_start_logic + r'\n    else:', content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Syntax error in bot.py fixed. Ready to launch.")
