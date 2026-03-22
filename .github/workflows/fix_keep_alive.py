import os
import re

file_path = r'c:\Users\user\Documents\Elyor\my-school-bot\bot_yangi.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add keep_alive_loop function (Clean version without triple-quote conflict)
keep_alive_code = r"""
async def keep_alive_loop():
    # Botni uxlab qolishidan himoya qilish (Anti-Sleep)
    await asyncio.sleep(60)
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(RENDER_URL) as resp:
                    if resp.status == 200:
                        logger.info("Keep-alive: Bot is awake! ✅")
        except:
            pass
        await asyncio.sleep(300) # 5 daqiqa
"""

# 2. Add / endpoint for root ping
if 'app.router.add_get("/map", handle_map)' in content:
    content = content.replace('app.router.add_get("/map", handle_map)', 
                              'app.router.add_get("/", lambda r: web.Response(text="Bot is online!") if r.method=="GET" else web.Response(status=405))\n    app.router.add_get("/map", handle_map)')

# 3. Add the logic to main() to start the loop
if 'asyncio.create_task(subscription_reminder_loop())' in content:
    content = content.replace('asyncio.create_task(subscription_reminder_loop())', 
                              'asyncio.create_task(subscription_reminder_loop())\n    asyncio.create_task(keep_alive_loop())')

# 4. Insert keep_alive_loop definition before main()
if 'async def main():' in content and 'async def keep_alive_loop():' not in content:
    content = content.replace('async def main():', keep_alive_code + '\nasync def main():')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Keep-alive system fixed and ready.")
