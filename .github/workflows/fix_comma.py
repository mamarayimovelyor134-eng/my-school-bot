import os

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the specific double comma that broke the dictionary
content = content.replace('"reg_success": "🎉 Muvaffaqiyatli ro\'yxatdan o\'tdingiz!",,', '"reg_success": "🎉 Muvaffaqiyatli ro\'yxatdan o\'tdingiz!",')

# Global cleanup for any other accidental double commas (carefully)
content = content.replace(',,', ',')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Double comma fixed.")
