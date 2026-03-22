import os
import re

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the reg_finish to include the keyboard (mkb)
new_reg_finish = r"""    if role == "driver":
        await m.answer("🎉 Muvaffaqiyatli ro'yxatdan o'tdingiz!\n🎁 Sizga haydovchi sifatida 30 kunlik bepul sinov muddati berildi!", reply_markup=await mkb(uid))
    else:
        await m.answer("🎉 Muvaffaqiyatli ro'yxatdan o'tdingiz!\n🚀 Botdan umrbod bepul foydalanishingiz mumkin. Safarni boshlash uchun quyidagi menyudan foydalaning!", reply_markup=await mkb(uid))
    await state.clear()"""

# We search for the previously inserted broken part and replace it
pattern = r'if role == \"driver\":.*?await state\.clear\(\)'
content = re.sub(pattern, new_reg_finish, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Full registration finish with keyboard restored.")
