@echo off
title International Taxi Bot - ZUKKO MEGA KUCH
echo Barcha eski botlar o'chirilmoqda...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im py.exe >nul 2>&1
echo ------------------------------------------
echo 📦 Kerakli kutubxonalar tekshirilmoqda...
echo ------------------------------------------
py -m pip install aiogram aiosqlite aiohttp asyncpg python-dotenv
echo ------------------------------------------
echo ✅ Tayyor! ZUKKO BOT ishga tushmoqda...
echo ------------------------------------------
py bot_yangi.py
pause
