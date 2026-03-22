import os

file_path = r'c:\Users\user\Documents\Elyor\my-school-bot\bot_yangi.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Restore server URL for 24/7 hosting
content = content.replace('RENDER_URL = "http://127.0.0.1:8081"', 'RENDER_URL = "https://taksi-bot-test.onrender.com"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Bot code prepared for server push.")
