import asyncio
import os
import logging
import aiohttp
import urllib.parse
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F, exceptions
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite
import asyncpg
from aiohttp import web
from dotenv import load_dotenv

# --- CONFIGURATION & ENV ---
load_dotenv()

# TOKEN validation
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else 0
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DB_URL = os.environ.get("DATABASE_URL")
DB_FILE = "school_bot.db"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
PORT = int(os.environ.get("PORT", 8080))

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SchoolBot")

# --- FSM STATES ---
class BotStates(StatesGroup):
    ADMIN_BROADCAST = State()

# --- DATABASE LAYER ---
db_pool = None

def sql_dialect(query):
    """Adapts queries between SQLite and PostgreSQL."""
    if DB_URL:
        placeholder_count = query.count('?')
        for i in range(1, placeholder_count + 1):
            query = query.replace('?', f'${i}', 1)
        query = query.replace('AUTOINCREMENT', '')
        # Basic PostgreSQL dialect fixes can be added here
    return query

async def init_db():
    global db_pool
    if DB_URL:
        try:
            db_pool = await asyncpg.create_pool(
                DB_URL.replace("postgres://", "postgresql://", 1),
                min_size=1, max_size=10
            )
            logger.info("✅ PostgreSQL pool initialized.")
        except Exception as e:
            logger.error(f"❌ PostgreSQL Error: {e}")

    await db_exec("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, username TEXT, reg_date TEXT)")
    logger.info("📦 DB Tables verified.")

async def db_exec(query, *args):
    query = sql_dialect(query)
    try:
        if DB_URL and db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute(query, *args)
        else:
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute(query, args)
                await db.commit()
    except Exception as e:
        logger.error(f"❌ DB Exec Error: {e} | Query: {query}")

async def db_fetch(query, *args, one=False):
    query = sql_dialect(query)
    try:
        if DB_URL and db_pool:
            async with db_pool.acquire() as conn:
                if one: return await conn.fetchrow(query, *args)
                return await conn.fetch(query, *args)
        else:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute(query, args) as cursor:
                    if one: return await cursor.fetchone()
                    return await cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ DB Fetch Error: {e}")
        return None

# --- KEYBOARDS ---
def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎨 Kreativ darslar"), types.KeyboardButton(text="📚 Darsliklar (1-11)"))
    return builder.as_markup(resize_keyboard=True)

def back_inline(cb="main_menu"):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🔙 Orqaga", callback_data=cb))
    return builder.as_markup()

# --- HANDLERS ---
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    reg_date = datetime.now().strftime("%Y-%m-%d")
    await db_exec("INSERT INTO users (user_id, username, reg_date) VALUES (?, ?, ?) ON CONFLICT (user_id) DO NOTHING", 
                  message.from_user.id, message.from_user.username, reg_date)
    await message.answer("🚀 *ZUKKO YORDAMCHI* botiga xush kelibsiz!\n\nBiz bilan ta'lim yanada oson va qiziqarli! 📚✨", 
                         parse_mode="Markdown", reply_markup=main_menu_kb())

# --- ADMIN PROTECTION & PANEL ---
@dp.message(Command("admin"))
async def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return # Silent protection
    
    users_raw = await db_fetch("SELECT COUNT(*) FROM users", one=True)
    count = users_raw[0] if users_raw else 0
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="📢 Hamshur xabar", callback_data="admin_broadcast"))
    builder.add(types.InlineKeyboardButton(text="📊 Statistikani yangilash", callback_data="admin_refresh"))
    
    await m.answer(f"👑 *ADMIN PANEL*\n\n📈 Foydalanuvchilar: {count}\n📅 Vaqt: {datetime.now().strftime('%H:%M')}", 
                   parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(c: types.CallbackQuery, state: FSMContext):
    if c.from_user.id != ADMIN_ID: return
    await state.set_state(BotStates.ADMIN_BROADCAST)
    await c.message.answer("📣 Yuboriladigan xabarni yozing (yoki rasm yuboring):")
    await c.answer()

@dp.message(BotStates.ADMIN_BROADCAST)
async def broadcast_send(m: types.Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    users = await db_fetch("SELECT user_id FROM users")
    await m.answer(f"⏳ {len(users)} ta foydalanuvchiga xabar yuborish boshlandi...")
    
    sent, failed = 0, 0
    for u in users:
        try:
            if m.text:
                await bot.send_message(u[0], m.text)
            elif m.photo:
                await bot.send_photo(u[0], m.photo[-1].file_id, caption=m.caption)
            sent += 1
            await asyncio.sleep(0.05) # Rate limiting
        except Exception:
            failed += 1
            
    await state.clear()
    await m.answer(f"✅ Tayyor!\n🚀 Yetkazildi: {sent}\n❌ Xatolik: {failed}", reply_markup=main_menu_kb())

# --- KREATIV DARSLAR ---
@dp.message(F.text == "🎨 Kreativ darslar")
async def show_kreativ(m: types.Message):
    res = "🎨 *KREATIV DARSLAR VA METODLAR* \n\n"
    res += "1. 🧩 *Domino metodi*: Zanjir hosil qilish o'yini.\n"
    res += "2. 💡 *Aqliy hujum*: Tezkor savol-javoblar.\n"
    res += "3. 🎨 *Sinkveyn*: 5 qatorli she'riy uslub.\n"
    res += "4. 🔍 *Klaster*: G'oyalar grafigi.\n"
    res += "5. 🎡 *Wordwall*: Interaktiv o'yinlar portali.\n\n"
    res += "Ma'lumot olish uchun tugmani bosing: 👇"
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🧩 Domino", callback_data="meth_domino"), types.InlineKeyboardButton(text="💡 Aqliy hujum", callback_data="meth_hujum"))
    builder.row(types.InlineKeyboardButton(text="🎨 Sinkveyn", callback_data="meth_sinkveyn"), types.InlineKeyboardButton(text="🔍 Klaster", callback_data="meth_klaster"))
    builder.row(types.InlineKeyboardButton(text="🎡 Wordwall Fanlar", callback_data="ww_subjects"))
    builder.row(types.InlineKeyboardButton(text="🏠 Menu", callback_data="main_menu"))
    await m.answer(res, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("meth_"))
async def method_info(c: types.CallbackQuery):
    m = c.data.split('_')[1]
    info = {
        "domino": "🧩 *Domino metodi:*\n\nO'quvchilar bir-biriga zanjir bo'lib savol berishadi. Birinchi o'quvchi savol beradi, ikkinchisi javob berib keyingi savolni qo'shadi.",
        "hujum": "💡 *Aqliy hujum:*\n\nMavzu bo'yicha cheklovsiz g'oyalarni yig'ish. Har qanday fikr qabul qilinadi, so'ngra eng yaxshilari tanlab olinadi.",
        "sinkveyn": "🎨 *Sinkveyn metodi:*\n\n1. Ot (mavzu)\n2. Sifat (2 ta)\n3. Fe'l (3 ta)\n4. Xulosa (4 ta so'z)\n5. Sinonim",
        "klaster": "🔍 *Klaster metodi:*\n\nTushunchalarni vizual guruhlash. Doska markaziga asosiy mavzu yoziladi va ushbu mavzu bilan bog'liq so'zlar atrofiga yozib chiqiladi."
    }
    await c.message.edit_text(info.get(m, "Ma'lumot topilmadi."), parse_mode="Markdown", reply_markup=back_inline("kreativ_back"))

@dp.callback_query(F.data == "kreativ_back")
async def back_kreativ(c: types.CallbackQuery):
    await show_kreativ(c.message)
    await c.answer()

@dp.callback_query(F.data == "ww_subjects")
async def wordwall_list(c: types.CallbackQuery):
    subs = [("Matematika", "matematika"), ("Ona tili", "ona-tili"), ("Ingliz tili", "english"), ("Fizika", "fizika"), ("Kimyo", "kimyo"), ("Tarix", "tarix")]
    builder = InlineKeyboardBuilder()
    for n, q in subs:
        builder.row(types.InlineKeyboardButton(text=f"📚 {n}", url=f"https://wordwall.net/uz-uz/community/{q}"))
    builder.row(types.InlineKeyboardButton(text="🔙 Orqaga", callback_data="kreativ_back"))
    await c.message.edit_text("🎡 *Fanlardan birini tanlang va Wordwall o'yinlarini ko'ring:*", parse_mode="Markdown", reply_markup=builder.as_markup())

# --- DARSLIKLAR ---
@dp.message(F.text == "📚 Darsliklar (1-11)")
async def show_grades(m: types.Message):
    builder = InlineKeyboardBuilder()
    for g in range(1, 12): builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"gr_{g}"))
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="main_menu"))
    await m.answer("📚 *Sinfingizni tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("gr_"))
async def book_sources(c: types.CallbackQuery):
    grade = c.data.split('_')[1]
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🏛 Kitob.uz (Rasmiy)", url="https://kitob.uz"))
    builder.row(types.InlineKeyboardButton(text="📘 Eduportal (Elektron)", url=f"http://eduportal.uz"))
    builder.row(types.InlineKeyboardButton(text="🔙 Orqaga", callback_data="gr_back"))
    await c.message.edit_text(f"📚 *{grade}-sinf darsliklari ushbu portallarda mavjud:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "gr_back")
async def back_grades(c: types.CallbackQuery):
    await show_grades(c.message)
    await c.answer()

@dp.callback_query(F.data == "main_menu")
async def go_home(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.delete()
    await c.message.answer("🏠 Asosiy menyu:", reply_markup=main_menu_kb())
    await c.answer()

# --- SERVER STABILITY ---
async def keep_alive():
    """Keeps the service alive on Render/Heroku."""
    if not RENDER_URL: return
    logger.info(f"🌐 Keep-alive module active. Target: {RENDER_URL}")
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(RENDER_URL, timeout=10) as resp:
                    if resp.status != 200: logger.warning(f"⚠️ Health signal abnormal: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Keep-alive Error: {e}")
        await asyncio.sleep(600) # Every 10 mins

async def handle_web(request):
    """Health check endpoint."""
    return web.Response(text="Bot is operational! 🚀", status=200)

async def main():
    if not TOKEN:
        logger.critical("BOT_TOKEN is missing!")
        return

    # Initialize DB with retry logic
    for attempt in range(3):
        try:
            await init_db()
            break
        except Exception as e:
            logger.error(f"DB attempt {attempt+1} failed: {e}")
            await asyncio.sleep(2)

    # Start Keep-alive
    asyncio.create_task(keep_alive())
    
    # Web server for 24/7 uptime monitoring
    try:
        app = web.Application()
        app.router.add_get("/", handle_web)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(f"🌐 Web health server started on port {PORT}")
    except Exception as e:
        logger.warning(f"⚠️ Web server could not start: {e}")
    
    # Start Polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ ZUKKO BOT is polling for updates...")
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    except Exception as e:
        logger.critical(f"❌ Polling Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot properly shutdown.")
    except Exception as e:
        logger.error(f"Fatal Startup Error: {e}")
