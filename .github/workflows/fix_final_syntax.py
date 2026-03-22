import os
import re

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken text with unterminated string
# We look for reg_finish and re-write the end part properly
# Find where role == 'driver' logic starts
pattern = r'if role == \"driver\":.*?await state\.clear\(\)'

# Using single quotes for the whole replacement block and careful with internal quotes
new_logic = '''    if role == "driver":
        await m.answer("🎉 Muvaffaqiyatli ro\\'yxatdan o\\'tdingiz!\\n🎁 Sizga haydovchi sifatida 30 kunlik bepul sinov muddati berildi!", reply_markup=await mkb(uid))
    else:
        await m.answer("🎉 Muvaffaqiyatli ro\\'yxatdan o\\'tdingiz!\\n🚀 Botdan umrbod bepul foydalanishingiz mumkin. Safarni boshlash uchun quyidagi menyudan foydalaning!", reply_markup=await mkb(uid))
    await state.clear()'''

if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_logic, content, flags=re.DOTALL)
else:
    # If pattern search fails, try to find by specific broken text
    content = content.replace('await m.answer("🎉 Muvaffaqiyatli ro\'yxatdan o\'tdingiz!\n', 'await m.answer("🎉 Muvaffaqiyatli ro\'yxatdan o\'tdingiz!\\n')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Syntax error at 393 fixed.")
