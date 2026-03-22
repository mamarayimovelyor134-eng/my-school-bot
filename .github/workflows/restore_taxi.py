import os

path_src = r'c:\Users\user\Documents\Elyor\TAXI.bot\taxi_system\taxi_bot.py'
path_dst = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'

# Read source
with open(path_src, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace token
old_token = 'BOT_TOKEN = "7920793706:AAFFooLG4Vh72XNOZfGasMNZPTeEq4YE9U4"'
new_token = 'BOT_TOKEN = "7920793706:AAGeDj3y5K7OPdTeXPoAaUeNYWoC49RipbM"'
content = content.replace(old_token, new_token)

# Write destination
with open(path_dst, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Taxi bot code restored to bot.py with new token.")
