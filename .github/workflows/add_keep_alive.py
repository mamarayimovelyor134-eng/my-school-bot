import os
import re

file_path = r'c:\Users\user\Documents\Elyor\my-school-bot\bot_yangi.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add keep_alive_loop function
keep_alive_code = r"""
async def keep_alive_loop():
    """Botni uxlab qolishidan himoya qilish uchun har 5 daqiqada o'zini o'zi 'ping' qiladi."""
    await asyncio.sleep(60) # Server to'liq yonishini kutamiz
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(RENDER_URL) as resp:
                    if resp.status == 200:
                        logger.info("Keep-alive: Bot is awake! ✅")
        except Exception as e:
            logger.error(f"Keep-alive error: {e}")
        await asyncio.sleep(300) # 5 daqiqa kutish
"""

# 2. Add / endpoint for root ping
content = content.replace('app.router.add_get("/map", handle_map)', 
                          'app.router.add_get("/", lambda r: web.Response(text="Bot is running! 🚀"))\n    app.router.add_get("/map", handle_map)')

# 3. Add the logic to main() to start the loop
content = content.replace('asyncio.create_task(subscription_reminder_loop())', 
                          'asyncio.create_task(subscription_reminder_loop())\n    asyncio.create_task(keep_alive_loop())')

# 4. Insert keep_alive_loop definition before main()
if 'async def main():' in content:
    content = content.replace('async def main():', keep_alive_code + '\nasync def main():')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Keep-alive system (Anti-sleep) added and ready.")
