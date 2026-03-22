import os

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Change RENDER_URL to local address for testing
old_url = 'RENDER_URL = "https://taksi-bot-test.onrender.com"'
new_url = 'RENDER_URL = "http://127.0.0.1:8081"' # Using local port 8081 as defined in main()

content = content.replace(old_url, new_url)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: RENDER_URL updated to local address for testing.")
