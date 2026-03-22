import os

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the escaped line 288
broken_line = r'await m\.answer\(t\(u\[6\], \"welcome\"\), parse_mode=\"Markdown\", reply_markup=await mkb\(m\.from_user\.id\)\)'
fixed_line = '        await m.answer(t(u[6], "welcome"), parse_mode="Markdown", reply_markup=await mkb(m.from_user.id))'

content = content.replace(broken_line, fixed_line)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Escaped line 288 fixed.")
