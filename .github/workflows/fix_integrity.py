import os
import re

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Change INSERT to INSERT OR REPLACE for users and drivers
content = content.replace('INSERT INTO users', 'INSERT OR REPLACE INTO users')
content = content.replace('INSERT INTO drivers', 'INSERT OR REPLACE INTO drivers')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: IntegrityError fixed with INSERT OR REPLACE.")
