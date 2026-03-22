import asyncio
import os
import logging
import random
import aiohttp
import base64
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

# --- LOAD CONFIG ---
load_dotenv()

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DB_URL = os.environ.get("DATABASE_URL")
DB_FILE = "school_bot.db"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

# --- FSM STATES ---
class BotStates(StatesGroup):
    AI_MODE = State()
    ADDING_TASK_TEXT = State()
    ADDING_TASK_TIME = State()
    ADMIN_BROADCAST = State()

# --- DATABASE HELPERS ---
db_pool = None

def sql_dialect(query):
    if DB_URL:
        placeholder_count = query.count('?')
        for i in range(1, placeholder_count + 1):
            query = query.replace('?', f'${i}', 1)
        query = query.replace('AUTOINCREMENT', '')
        query = query.replace('ON CONFLICT (user_id) DO NOTHING', 'ON CONFLICT (user_id) DO NOTHING')
    return query

async def init_db():
    global db_pool
    if DB_URL:
        try:
            db_pool = await asyncpg.create_pool(
                DB_URL.replace("postgres://", "postgresql://", 1),
                min_size=1, max_size=10
            )
            logger.info("✅ PostgreSQL ulanishi muvaffaqiyatli.")
        except Exception as e:
            logger.error(f"❌ PostgreSQL xatosi: {e}")

    await db_exec("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, username TEXT, reg_date TEXT)")
    if DB_URL:
        await db_exec("CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, user_id BIGINT, task_text TEXT, remind_time TEXT, created_at TEXT, is_done BOOLEAN DEFAULT FALSE)")
    else:
        await db_exec("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id BIGINT, task_text TEXT, remind_time TEXT, created_at TEXT, is_done BOOLEAN DEFAULT 0)")
    logger.info("📦 Database jadvallari tayyor.")

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
        logger.error(f"❌ DB Exec Error: {e}")

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

# --- AI & CONTENT DATA ---
async def ask_ai(question: str, image_b64: str = None) -> str:
    if GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        parts = [{"text": question}]
        if image_b64:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_b64}})
        payload = {"contents": [{"parts": parts}]}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=25) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]
        except: pass
    
    if not image_b64:
        system = "Sen o'zbek maktab o'quvchilariga yordam beruvchi aqlli AI yordamchisan."
        url = f"https://text.pollinations.ai/{urllib.parse.quote(question)}?model=openai&system={urllib.parse.quote(system)}&json=false"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=20) as resp:
                    if resp.status == 200: return await resp.text()
        except: pass
    return "❌ Uzr, hozircha bu so'rovni bajarib bo'lmaydi."

KREATIV_DATA = [
    ("🧩 Domino metodi", "Mavzuni tushunish uchun zanjir hosil qilish o'yini."),
    ("💡 Aqliy hujum", "Tezkor va kreativ savol-javoblar."),
    ("🎨 Sinkveyn", "Beshta qatordan iborat she'riy uslub."),
    ("🔍 Klaster", "G'oyalarni jamlash uchun grafik chizish."),
    ("🎡 Wordwall", "Interaktiv o'yinlar va qiziqarli viktorinalar yaratish platformasi.")
]

QUIZ_DATA = [
    {"q": "O'zbekiston poytaxti qaysi?", "o": ["Toshkent", "Samarqand", "Buxoro"], "a": "Toshkent"},
    {"q": "2x2 necha bo'ladi?", "o": ["3", "4", "5"], "a": "4"},
    {"q": "Inson tanasidagi eng katta a'zo?", "o": ["Jigar", "Teri", "Yurak"], "a": "Teri"}
]

# --- KEYBOARDS ---
def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎨 Kreativ darslar"), types.KeyboardButton(text="📚 Darsliklar (1-11)"))
    builder.row(types.KeyboardButton(text="📊 BSB (Nazorat)"), types.KeyboardButton(text="📅 Taqvim rejalar"))
    builder.row(types.KeyboardButton(text="🎥 Video darslar"), types.KeyboardButton(text="📝 Onlayn testlar"))
    builder.row(types.KeyboardButton(text="🤖 AI Yordamchi"), types.KeyboardButton(text="🧩 Bilim testi"))
    builder.row(types.KeyboardButton(text="🌍 G'aroyib Faktlar"), types.KeyboardButton(text="💡 Motivatsiya"))
    builder.row(types.KeyboardButton(text="📝 Vazifalarim"))
    return builder.as_markup(resize_keyboard=True)

def back_inline():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu"))
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
    await message.answer("🚀 *ZUKKO YORDAMCHI PILOT* botiga xush kelibsiz!\n\nBiz bilan ta'lim yanada oson va qiziqarli! 📚✨", 
                         parse_mode="Markdown", reply_markup=main_menu_kb())

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    res = await db_fetch("SELECT COUNT(*) FROM users", one=True)
    count = res[0] if res else 0
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="📢 Hamshur xabar", callback_data="admin_broadcast"))
    await m.answer(f"👑 *ADMIN PANEL*\n\n📊 Foydalanuvchilar soni: {count}", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.ADMIN_BROADCAST)
    await c.message.answer("📣 Hammaga yuboriladigan xabarni yozing:")
    await c.answer()

@dp.message(BotStates.ADMIN_BROADCAST)
async def broadcast_send(m: types.Message, state: FSMContext):
    users = await db_fetch("SELECT user_id FROM users")
    await m.answer("⏳ Xabar yuborish boshlandi...")
    sent = 0
    for u in users:
        try:
            await bot.send_message(u[0], m.text)
            sent += 1
            await asyncio.sleep(0.05)
        except: continue
    await state.clear()
    await m.answer(f"✅ Xabar {sent} ta foydalanuvchiga yetkazildi.")

# --- SECTIONS ---
@dp.message(F.text == "🎨 Kreativ darslar")
async def show_kreativ(m: types.Message):
    res = "🎨 *KREATIV DARSLAR VA INTERAKTIV METODLAR* \n\n"
    res += "1. 🧩 *Domino metodi*: Mavzuni tushunish uchun zanjir hosil qilish o'yini.\n"
    res += "2. 💡 *Aqliy hujum*: Tezkor va kreativ savol-javoblar.\n"
    res += "3. 🎨 *Sinkveyn*: Beshta qatordan iborat she'riy uslub.\n"
    res += "4. 🔍 *Klaster*: G'oyalarni jamlash uchun grafik chizish.\n"
    res += "5. 🎡 *Wordwall*: Interaktiv o'yinlar va viktorinalar.\n\n"
    res += "Qaysi yo'nalish bo'yicha yordam yoki havola kerak?"
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🧩 Domino", callback_data="meth_domino"), types.InlineKeyboardButton(text="💡 Aqliy hujum", callback_data="meth_hujum"))
    builder.row(types.InlineKeyboardButton(text="🎨 Sinkveyn", callback_data="meth_sinkveyn"), types.InlineKeyboardButton(text="🔍 Klaster", callback_data="meth_klaster"))
    builder.row(types.InlineKeyboardButton(text="🎡 Wordwall Fanlar", callback_data="ww_subjects"))
    builder.row(types.InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu"))
    await m.answer(res, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("meth_"))
async def show_method_info(c: types.CallbackQuery):
    meth = c.data.split('_')[1]
    info = {
        "domino": "🧩 *Domino metodi:*\n\nBu metodda mavzuga oid tushunchalar zanjir shaklida ulanadi. Masalan, bir o'quvchi savol beradi, keyingisi javobini aytib o'zi yangi savol qo'shadi.",
        "hujum": "💡 *Aqliy hujum (Brainstorming):*\n\nMavzu bo'yicha har qanday g'oyalarni (hatto eng sodda bo'lsa ham) tezkor yig'ish usuli. Tanqid taqiqlanadi, faqat ko'p va kreativ g'oyalar to'planadi.",
        "sinkveyn": "🎨 *Sinkveyn metodi:*\n\n5 qatorli she'r usuli:\n1. Mavzu (1 ta ot)\n2. Ta'rif (2 ta sifat)\n3. Harakat (3 ta fe'l)\n4. Xulosa (4 ta so'z)\n5. Sinonim (1 ta so'z)",
        "klaster": "🔍 *Klaster (Tarmoqlar) metodi:*\n\nAsosiy tushunchani markazga yozib, unga bog'liq barcha so'z va ma'lumotlarni shoxlar ko'rinishida yozib chiqish."
    }
    await c.message.edit_text(info.get(meth, "Ma'lumot topilmadi."), parse_mode="Markdown", reply_markup=back_inline())

@dp.callback_query(F.data == "ww_subjects")
async def wordwall_subjects(c: types.CallbackQuery):
    subjects = [
        ("Matematika", "matematika"),
        ("Ona tili", "ona-tili"),
        ("Ingliz tili", "english"),
        ("Fizika", "fizika"),
        ("Kimyo", "kimyo"),
        ("Biologiya", "biologiya"),
        ("Tarix", "tarix"),
        ("Geografiya", "geografiya")
    ]
    builder = InlineKeyboardBuilder()
    for name, query in subjects:
        builder.row(types.InlineKeyboardButton(
            text=f"📚 {name}", 
            url=f"https://wordwall.net/uz-uz/community/{query}"
        ))
    builder.row(types.InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu"))
    await c.message.edit_text("🎡 *Fanlardan birini tanlang va tayyor o'yinlarni ko'ring:*", 
                             parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.message(F.text == "📚 Darsliklar (1-11)")
async def show_grades(m: types.Message):
    builder = InlineKeyboardBuilder()
    for g in range(1, 12): builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"gr_{g}"))
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="main_menu"))
    await m.answer("📚 *Sinfingizni tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "main_menu")
async def go_home(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text("🏠 Asosiy menyu:")
    await c.message.answer("Foydalanishda davom eting 👇", reply_markup=main_menu_kb())
    await c.answer()

@dp.callback_query(F.data.startswith("gr_"))
async def show_books(c: types.CallbackQuery):
    grade = c.data.split('_')[1]
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🏛 Kitob.uz", url="https://kitob.uz"))
    builder.row(types.InlineKeyboardButton(text="📘 Eduportal", url=f"http://eduportal.uz"))
    builder.row(types.InlineKeyboardButton(text="🔙 Orqaga", callback_data="gr_list"))
    await c.message.edit_text(f"📚 *{grade}-sinf uchun darsliklar manbalari:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "gr_list")
async def back_to_grades(c: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for g in range(1, 12): builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"gr_{g}"))
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="main_menu"))
    await c.message.edit_text("📚 *Sinfingizni tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.message(F.text == "🎥 Video darslar")
async def show_videos(m: types.Message):
    await m.answer("🎥 *VIDEO DARSLAR PORTALLARI* \n\n🔹 [Maktab.uz](https://maktab.uz/)\n🔹 [IT-Park YouTube](https://youtube.com/@itpark)\n🔹 [Kundalik.com](https://kundalik.com/)", 
                   parse_mode="Markdown", reply_markup=back_inline(), disable_web_page_preview=True)

@dp.message(F.text == "📝 Onlayn testlar")
async def show_online_tests(m: types.Message):
    await m.answer("📝 *ONLAYN TEST TOPSHIRISH* \n\n🔹 [DTM.uz](https://dtm.uz/)\n🔹 [Test.uz](https://test.uz/)\n🔹 [Prep.uz](https://prep.uz/)", 
                   parse_mode="Markdown", reply_markup=back_inline(), disable_web_page_preview=True)

@dp.message(F.text == "📊 BSB (Nazorat)")
async def show_bsb(m: types.Message):
    await m.answer("📊 *BSB (Baho-Sifat-Baholash)* \n\nHozirda bu bo'limda imtihon namunalari tayyorlanmoqda. Rasm yuborsangiz AI yechib beradi! 🤖", reply_markup=back_inline())

@dp.message(F.text == "📅 Taqvim rejalar")
async def show_taqvim(m: types.Message):
    await m.answer("📅 *TAQVIM-MAVZU REJALAR* \n\nBarcha fanlar bo'yicha rejalarni [Maktab.uz](https://maktab.uz/planning) bo'limidan olishingiz mumkin.", reply_markup=back_inline(), parse_mode="Markdown")

@dp.message(F.text == "🤖 AI Yordamchi")
async def ai_start(m: types.Message, state: FSMContext):
    await state.set_state(BotStates.AI_MODE)
    kb = ReplyKeyboardBuilder()
    kb.add(types.KeyboardButton(text="❌ Bekor qilish"))
    await m.answer("🤖 *ZUKKO AI REJIMI* \n\nIstalgan savolingizni yuboring, men tahlil qilaman. ✨", 
                   reply_markup=kb.as_markup(resize_keyboard=True), parse_mode="Markdown")

@dp.message(BotStates.AI_MODE, F.text == "❌ Bekor qilish")
async def ai_exit(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("Oddiy menyuga qaytdingiz.", reply_markup=main_menu_kb())

@dp.message(BotStates.AI_MODE)
async def ai_process(m: types.Message):
    if not m.text: return
    wait = await m.answer("⏳ _O'ylanmoqdaman..._")
    res = await ask_ai(m.text)
    await wait.edit_text(f"🤖 *ZUKKO JAVOBI:* \n\n{res}", parse_mode="Markdown")

@dp.message(F.text == "🧩 Bilim testi")
async def show_quiz(m: types.Message):
    q = random.choice(QUIZ_DATA)
    builder = InlineKeyboardBuilder()
    for o in q['o']: builder.row(types.InlineKeyboardButton(text=o, callback_data=f"ans_{o}_{q['a']}"))
    await m.answer(f"🧩 *SAVOL:* \n{q['q']}", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("ans_"))
async def check_quiz(c: types.CallbackQuery):
    _, ans, correct = c.data.split('_')
    if ans == correct: await c.answer("✅ To'g'ri topdingiz!", show_alert=True)
    else: await c.answer(f"❌ Noto'g'ri. To'g'ri javob: {correct}", show_alert=True)
    await c.message.delete()

# --- TASK MANAGEMENT ---
@dp.message(F.text == "📝 Vazifalarim")
async def show_tasks(m: types.Message):
    tasks = await db_fetch("SELECT id, task_text, remind_time FROM tasks WHERE user_id = ? AND is_done = ?", 
                           m.from_user.id, False if DB_URL else 0)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="➕ Yangi", callback_data="add_task"))
    if tasks: builder.add(types.InlineKeyboardButton(text="🗑 Hammasini o'chirish", callback_data="clear_tasks"))
    
    res = "📝 *SIZNING VAZIFALARINGIZ:* \n\n"
    if not tasks: res += "Hozircha vazifalar yo'q. Yangi qo'shish uchun tugmani bosing. 👇"
    else:
        for t in tasks:
            res += f"📌 *{t[1]}* \n⏰ Vaqt: `{t[2]}`\n/done_{t[0]} - Bajarildi\n\n"
    await m.answer(res, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "clear_tasks")
async def clear_all_tasks(c: types.CallbackQuery):
    await db_exec("DELETE FROM tasks WHERE user_id = ?", c.from_user.id)
    await c.message.edit_text("✅ Barcha vazifalar o'chirildi.", reply_markup=back_inline())
    await c.answer()

@dp.callback_query(F.data == "add_task")
async def task_init(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.ADDING_TASK_TEXT)
    kb = ReplyKeyboardBuilder()
    kb.add(types.KeyboardButton(text="❌ Bekor qilish"))
    await c.message.answer("📝 Vazifa nima? Masalan: _Matematika misollari_", reply_markup=kb.as_markup(resize_keyboard=True))
    await c.answer()

@dp.message(F.text == "❌ Bekor qilish")
async def cancel_action(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("Amal bekor qilindi.", reply_markup=main_menu_kb())

@dp.message(BotStates.ADDING_TASK_TEXT)
@dp.message(BotStates.AI_MODE) # Also handle if user is in AI mode
async def task_text_save(m: types.Message, state: FSMContext):
    if await state.get_state() == BotStates.AI_MODE:
        if m.text == "❌ Bekor qilish":
            await state.clear()
            await m.answer("AI rejimdan chiqdingiz.", reply_markup=main_menu_kb())
            return
        # If not cancel, proceed to AI
        await ai_process(m)
        return

    await state.update_data(txt=m.text)
    await state.set_state(BotStates.ADDING_TASK_TIME)
    kb = ReplyKeyboardBuilder()
    kb.add(types.KeyboardButton(text="❌ Bekor qilish"))
    await m.answer("⏰ Qachon eslatay? (Format: 08:00, 15:30)", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(BotStates.ADDING_TASK_TIME)
async def task_time_save(m: types.Message, state: FSMContext):
    if m.text == "❌ Bekor qilish":
        await state.clear()
        await m.answer("Amal bekor qilindi.", reply_markup=main_menu_kb())
        return

    time_str = m.text.replace(".", ":").replace(" ", "").strip()
    if ":" not in time_str:
        if len(time_str) >= 1 and len(time_str) <= 2: time_str += ":00"
        else: return await m.answer("❌ Noto'g'ri vaqt. Iltimos 08:00 kabi yozing!")
    
    data = await state.get_data()
    now = datetime.now().strftime("%Y-%m-%d")
    await db_exec("INSERT INTO tasks (user_id, task_text, remind_time, created_at) VALUES (?, ?, ?, ?)", 
                  m.from_user.id, data['txt'], time_str, now)
    await state.clear()
    await m.answer(f"✅ Vazifa saqlandi!\n📍 {data['txt']}\n⏰ {time_str}", reply_markup=main_menu_kb())

@dp.message(F.text.startswith("/done_"))
async def mark_task_done(m: types.Message):
    try:
        tid = int(m.text.split('_')[1])
        await db_exec("UPDATE tasks SET is_done = ? WHERE id = ?", True if DB_URL else 1, tid)
        await m.answer("🎉 Barakalla! Vazifa bajarildi deb belgilandi.")
    except: await m.answer("❌ Xatolik yuz berdi.")

# --- UTILS ---
@dp.message(F.text == "💡 Motivatsiya")
async def show_mot(m: types.Message):
    quotes = [
        "🌟 Bugungi harakatingiz — ertangi muvaffaqiyatingiz poydevoridir!",
        "🚀 To'xtab qolmang! Hatto eng kichik qadam ham sizni maqsad sari yetaklaydi.",
        "🧠 Bilim — bu eng katta boylik. Uni hech kim sizdan tortib ololmaydi.",
        "🔥 Iroda bo'lsa, yo'l topiladi. Harakatni hoziroq boshlang!",
        "💎 Qiyinchiliklar sizni kuchli qiladi. Taslim bo'lish — ojizlar ishi."
    ]
    await m.answer(f"✨ *Siz uchun motivatsiya:*\n\n{random.choice(quotes)}", parse_mode="Markdown")

@dp.message(F.text == "🌍 G'aroyib Faktlar")
async def show_fact(m: types.Message):
    facts = [
        "🌍 Dunyodagi eng uzun daryo — Nil daryosi (6,650 km).",
        "Antarktida — dunyodagi eng qurg'oqchil qit'a, u yerda 2 million yildan buyon yomg'ir yog'magan hududlar bor.",
        "🐜 Chumolilar o'z vaznidan 50 baravar og'ir yukni ko'tara oladilar.",
        "🐘 Fillar sakray olmaydigan yagona sutemizuvchilardir.",
        "🌊 Dunyo okeanining faqat 5% qismi o'rganilgan.",
        "🍯 Asal hech qachon buzilmaydigan yagona oziq-ovqat mahsulotidir.",
        "📱 Dunyodagi birinchi mobil telefon Motorola kompanayasi tomonidan 1973-yilda yaratilgan."
    ]
    await m.answer(f"🧐 *Bilasizmi?*\n\n{random.choice(facts)}", parse_mode="Markdown")

@dp.message(F.photo)
async def process_photo(m: types.Message):
    wait = await m.answer("⏳ _AI rasm tahlili boshlandi..._")
    try:
        file = await bot.get_file(m.photo[-1].file_id)
        # Download strictly using the integrated download method
        destination = f"temp_{m.from_user.id}.jpg"
        await bot.download_file(file.file_path, destination)
        
        with open(destination, "rb") as image_file:
            img_b64 = base64.b64encode(image_file.read()).decode('utf-8')
        
        os.remove(destination) # Clean up
        
        prompt = "Mana shu rasmda nima borligini aytib ber, va undagi savol/masalani yechib ber: " + (m.caption or "")
        res = await ask_ai(prompt, img_b64)
        await wait.edit_text(f"✅ *AI TAHLIL NATIJASI* \n\n{res}", parse_mode="Markdown")
    except Exception as e:
        await wait.edit_text(f"❌ Xatolik: {e}")

@dp.message()
async def default_echo(m: types.Message):
    await m.answer("Pastdagi menyudan foydalaning 👇", reply_markup=main_menu_kb())

# --- RUN ---
async def reminder_loop():
    while True:
        now = datetime.now().strftime("%H:%M")
        res = await db_fetch("SELECT id, user_id, task_text FROM tasks WHERE remind_time = ? AND is_done = ?", 
                             now, False if DB_URL else 0)
        if res:
            for r in res:
                try:
                    await bot.send_message(r[1], f"⏰ *VAQT BO'LDI!* \n📌 {r[2]}")
                    await db_exec("UPDATE tasks SET is_done = ? WHERE id = ?", True if DB_URL else 1, r[0])
                except: pass
        await asyncio.sleep(60)

async def keep_alive():
    if not RENDER_URL: return
    while True:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(RENDER_URL) as r: logger.info(f"Ping: {r.status}")
        except: pass
        await asyncio.sleep(300)

async def handle_web(request): return web.Response(text="Success! 🚀")

async def main():
    if not TOKEN:
        logger.critical("❌ BOT_TOKEN TOPILMADI!")
        return
    
    try:
        await init_db()
    except Exception as e:
        logger.error(f"DB Init Error: {e}")

    asyncio.create_task(reminder_loop())
    asyncio.create_task(keep_alive())
    
    # Web server optional check - if port is busy, don't crash
    try:
        app = web.Application()
        app.router.add_get("/", handle_web)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
        await site.start()
        logger.info("🌐 Web server tayyor.")
    except Exception as e:
        logger.warning(f"⚠️ Web server ishga tushmadi (lokal ishlash uchun ahamiyatsiz): {e}")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ ZUKKO BOT muvaffaqiyatli ishga tushdi!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"❌ Polling Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
