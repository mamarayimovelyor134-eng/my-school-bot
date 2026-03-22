import os
import re

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Change the reg_success message for passengers specifically
# We'll update the TEXTS dictionary to have separate messages or modify wait_answer
content = content.replace('"reg_success": "🎉 Muvaffaqiyatli ro\'yxatdan o\'tdingiz!\\n🎁 30 kunlik sinov muddati berildi!"', 
                          '"reg_success": "🎉 Muvaffaqiyatli ro\'yxatdan o\'tdingiz!",')

# Now update the code that sends the message to be clearer for passengers
new_msg_logic = r"""    
    if role == "driver":
        await m.answer("🎉 Muvaffaqiyatli ro'yxatdan o'tdingiz!\n🎁 Sizga haydovchi sifatida 30 kunlik bepul sinov muddati berildi!")
    else:
        await m.answer("🎉 Muvaffaqiyatli ro'yxatdan o'tdingiz!\n🚀 Botdan umrbod bepul foydalanishingiz mumkin. Safarni boshlash uchun /start bosing yoki quyidagi menyudan foydalaning!")
    await state.clear()"""

# Replace the part of reg_finish that sends reg_success
pattern = r'await m\.answer\(TEXTS\[lang\]\[\"reg_success\"\](.*?)\s+if role == \"driver\":.*?await state\.clear\(\)'
content = re.sub(pattern, new_msg_logic, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Passenger message is now unlimited/free forever.")
