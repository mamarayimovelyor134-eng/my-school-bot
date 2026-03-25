import asyncio
import os
import logging
import json
import math
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import WebAppInfo
import aiosqlite
from aiohttp import web
# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- LOAD ENVIRONMENT ---
from dotenv import load_dotenv
load_dotenv()

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_FILE = "taxi_bot.db"
TRIAL_DAYS = 30
DAILY_FEE = 5000
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "398062627:TEST:999999999")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://taksi-bot-test.onrender.com")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# --- TRANSLATIONS (I18N) ---
TEXTS = {
    "uz": {
        "welcome": "👋 *Assalomu alaykum!* \nQishloq-Shahar Taksi botiga xush kelibsiz! ✨\n\n⚠️ *MUHIM:* Bot faqat vositachi hisoblanadi va nizolar uchun javobgar emas.",
        "choose_role": "Siz kimsiz? 👇",
        "role_driver": "👨‍✈️ Haydovchiman",
        "role_passenger": "👤 Yo'lovchiman",
        "enter_name": "Ism-familiyangizni kiriting:",
        "enter_car": "Mashinangiz rusumini kiriting:",
        "enter_number": "Mashina raqamini kiriting:",
        "select_region": "Hududingizni tanlang:",
        "select_route_from": "Qayerdan qatnaysiz? (Yo'nalish):",
        "select_route_to": "Qayerga borasiz? (Yo'nalish):",
        "enter_phone": "Telefon raqamingizni yuboring:",
        "reg_success": "🎉 Muvaffaqiyatli ro'yxatdan o'tdingiz!\n🎁 Sizga 30 kunlik sinov muddati berildi!",
        "main_driver": "🚕 Haydovchi paneli",
        "main_order": "📢 Buyurtma berish",
        "main_search": "🔍 Qidirish",
        "main_profile": "👤 Profilim",
        "main_balance": "📊 Balans",
        "main_sos": "🆘 SOS",
        "ask_location": "Sizga yaqin haydovchilarni topish uchun joylashuvingizni yuboring 👇",
        "loc_updated": "✅ Joylashuvingiz yangilandi!",
        "suggested_price": "📍 Tavsiya qilingan narx: *{price} so'm*\n💰 O'z narxingizni taklif qiling:",
        "sos_sent": "🚨 *SOS XABARI:* Yo'lovchi yordam so'ramoqda! \nFoydalanuvchi: {user}\nJoylashuv: {link}",
        "order_sent_all": "✅ Buyurtmangiz barcha faol haydovchilarga yuborildi!",
        "top_up": "💳 Balansni to'ldirish",
        "main_support": "📩 Adminga yozish",
        "support_ask": "📝 Adminga xabaringizni yozing (taklif, shikoyat yoki savol):",
        "support_sent": "✅ Xabaringiz adminga yuborildi! Tez orada javob beramiz.",
        "switch_to_driver": "👨‍✈️ Haydovchilikka o'tish",
        "switch_to_passenger": "👤 Yo'lovchilikka o'tish",
        "role_changed": "✅ Role muvaffaqiyatli o'zgartirildi!",
        "choose_options": "Qo'shimcha imkoniyatlar kerakmi?",
        "send_location": "📍 Joylashuvni yuborish",
    },
    "ru": {
        "welcome": "👋 *Здравствуйте!* \nДобро пожаловать в бот Село-Город Такси! ✨\n\n⚠️ *ВАЖНО:* Бот является посредником и не несет ответственности за споры.",
        "choose_role": "Кто вы? 👇",
        "role_driver": "👨‍✈️ Водитель",
        "role_passenger": "👤 Пассажир",
        "enter_name": "Введите ваше имя и фамилию:",
        "enter_car": "Введите модель машины:",
        "enter_number": "Введите номер машины:",
        "select_region": "Выберите ваш регион:",
        "select_route_from": "Откуда вы ездите? (Маршрут):",
        "select_route_to": "Куда вы ездите? (Маршрут):",
        "enter_phone": "Отправьте ваш номер телефона:",
        "reg_success": "🎉 Вы успешно зарегистрированы!\n🎁 Вам предоставлен пробный период на 30 дней!",
        "main_driver": "🚕 Панель водителя",
        "main_order": "📢 Сделать заказ",
        "main_search": "🔍 Поиск",
        "main_profile": "👤 Профиль",
        "main_balance": "📊 Баланс",
        "main_sos": "🆘 SOS",
        "ask_location": "Отправьте местоположение, чтобы найти водителей рядом 👇",
        "loc_updated": "✅ Ваше местоположение обновлено!",
        "suggested_price": "📍 Рекомендуемая цена: *{price} сум*\n💰 Предложите свою цену:",
        "sos_sent": "🚨 *SOS:* Пассажир просит помощи! \nПользователь: {user}\nЛокация: {link}",
        "order_sent_all": "✅ Ваш заказ отправлен всем активным водителям на карте!",
        "top_up": "💳 Пополнить баланс",
        "main_support": "📩 Написать админу",
        "support_ask": "📝 Напишите ваше сообщение админу (предложение, жалоба или вопрос):",
        "support_sent": "✅ Ваше сообщение отправлено админу! Мы скоро ответим.",
        "switch_to_driver": "👨‍✈️ Стать водителем",
        "switch_to_passenger": "👤 Стать пассажиром",
        "role_changed": "✅ Роль успешно изменена!",
    },
    "en": {
        "welcome": "👋 *Hello!* \nWelcome to Village-City Taxi bot! ✨\n\n⚠️ *IMPORTANT:* Bot is a mediator and not responsible for any disputes.",
        "choose_role": "Who are you? 👇",
        "role_driver": "👨‍✈️ Driver",
        "role_passenger": "👤 Passenger",
        "enter_name": "Enter your full name:",
        "enter_car": "Enter car model:",
        "enter_number": "Enter car number:",
        "select_region": "Select your region:",
        "select_route_from": "Where do you drive from? (Route):",
        "select_route_to": "Where do you drive to? (Route):",
        "enter_phone": "Send your phone number:",
        "reg_success": "🎉 Successfully registered!\n🎁 30 days trial granted!",
        "main_driver": "🚕 Driver Panel",
        "main_order": "📢 Place Order",
        "main_search": "🔍 Search",
        "main_profile": "👤 Profile",
        "main_balance": "📊 Balance",
        "main_sos": "🆘 SOS",
        "ask_location": "Send your location to find nearby drivers 👇",
        "loc_updated": "✅ Location updated!",
        "suggested_price": "📍 Suggested price: *{price} UZS*\n💰 Offer your price:",
        "sos_sent": "🚨 *SOS:* Passenger needs help! \nUser: {user}\nLocation: {link}",
        "order_sent_all": "✅ Your order has been sent to all active drivers on the map!",
        "top_up": "💳 Top up Balance",
        "main_support": "📩 Contact Admin",
        "support_ask": "📝 Write your message to admin (suggestion, complaint or question):",
        "support_sent": "✅ Your message has been sent! We will reply soon.",
        "switch_to_driver": "👨‍✈️ Become a driver",
        "switch_to_passenger": "👤 Become a passenger",
        "role_changed": "✅ Role successfully changed!",
    }
}
# --- REGION COORDINATES (Estimation) ---
REGION_COORDS = {
    "Toshkent": (41.3110, 69.2405), "Andijon": (40.7820, 72.3442), "Farg'ona": (40.3842, 71.7843),
    "Namangan": (40.9983, 71.6726), "Buxoro": (39.7747, 64.4286), "Samarqand": (39.6508, 66.9654),
    "Xorazm": (41.5583, 60.6138), "Navoiy": (40.1039, 65.3736), "Qashqadaryo": (38.8610, 65.7847),
    "Surxondaryo": (37.2242, 67.2783), "Jizzax": (40.1158, 67.8422), "Sirdaryo": (40.4851, 68.7847),
    "Qoraqalpog'iston": (42.4603, 59.6133)
}
def haversine(c1, c2):
    R = 6371 # Earth radius in km
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))
# --- STATES ---
class RegState(StatesGroup):
    choosing_lang = State()
    choosing_role = State()
    entering_name = State()
    entering_car = State()
    entering_number = State()
    selecting_route_from = State()
    selecting_route_to = State()
    selecting_region = State()
    entering_phone = State()
    selecting_car_features = State()
class OrderState(StatesGroup):
    choosing_origin = State()
    choosing_destination = State()
    entering_location = State()
    entering_price = State()
    choosing_filters = State()
    searching_driver = State()
class DriverState(StatesGroup):
    updating_loc = State()
class CounterOffer(StatesGroup):
    entering_price = State()
    confirm_offer = State()
class AdminState(StatesGroup):
    entering_ad = State()
    confirm_ad = State()
class SetSOS(StatesGroup):
    entering_id = State()
class SupportState(StatesGroup):
    entering_msg = State()
# --- DB INIT ---
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, 
            phone TEXT, role TEXT, reg_date TEXT, lang TEXT DEFAULT 'uz', 
            sos_contact_id INTEGER, referred_by INTEGER, referral_count INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS drivers (
            user_id INTEGER PRIMARY KEY, car_model TEXT, car_number TEXT, region TEXT, 
            route_from TEXT, route_to TEXT, status INTEGER DEFAULT 0, balance INTEGER DEFAULT 0, 
            trial_ends_at TEXT, last_payment_date TEXT, lat REAL, lon REAL, 
            rating_sum INTEGER DEFAULT 0, rating_count INTEGER DEFAULT 0,
            has_ac INTEGER DEFAULT 0, large_trunk INTEGER DEFAULT 0, female_driver INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, origin TEXT, 
            destination TEXT, price TEXT, status TEXT DEFAULT 'open', 
            created_at TEXT, lat REAL, lon REAL, driver_id INTEGER, 
            has_ac INTEGER DEFAULT 0, large_trunk INTEGER DEFAULT 0)""")
        await db.commit()
# --- UTILS ---
async def get_user_db(uid):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (uid,)) as c: return await c.fetchone()
async def get_driver_db(uid):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT * FROM drivers WHERE user_id = ?", (uid,)) as c: return await c.fetchone()
async def get_lang(uid):
    u = await get_user_db(uid)
    return u[6] if u else "uz"
def t(uid_or_lang, key):
    lang = uid_or_lang if isinstance(uid_or_lang, str) else "uz" # Simplified for now
    return TEXTS.get(lang, TEXTS["uz"]).get(key, key)
# --- KEYBOARDS ---
def lang_kb():
    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"))
    b.add(types.InlineKeyboardButton(text="🇷🇺 ╨а╤Г╤Б╤Б╨║╨╕╨╣", callback_data="lang_ru"))
    b.add(types.InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"))
    return b.as_markup()
async def mkb(uid):
    lang = await get_lang(uid)
    u = await get_user_db(uid)
    tx = TEXTS[lang]
    b = ReplyKeyboardBuilder()
    map_url = f"{RENDER_URL}/map"
    if u and u[4] == "driver":
        # Driver Menu
        b.row(types.KeyboardButton(text=tx["main_driver"]), types.KeyboardButton(text=tx["main_order"]))
        b.row(types.KeyboardButton(text="📜 Mening buyurtmalarim"), types.KeyboardButton(text="🗺 Xarita", web_app=WebAppInfo(url=map_url)))
        b.row(types.KeyboardButton(text=tx["main_balance"]), types.KeyboardButton(text=tx["main_sos"]))
    else:
        # Passenger Menu
        b.row(types.KeyboardButton(text=tx["main_order"]), types.KeyboardButton(text=tx["main_search"]))
        b.row(types.KeyboardButton(text="📜 Mening buyurtmalarim"), types.KeyboardButton(text=tx["main_profile"]))
        b.row(types.KeyboardButton(text="🗺 Xarita", web_app=WebAppInfo(url=map_url)), types.KeyboardButton(text=tx["main_sos"]))
        b.row(types.KeyboardButton(text="🚖 Haydovchi bo'lib ishlash"))
    b.row(types.KeyboardButton(text=tx["main_support"]))
    return b.as_markup(resize_keyboard=True)
def reg_regions_kb():
    b = InlineKeyboardBuilder()
    for r in REGION_COORDS.keys(): b.add(types.InlineKeyboardButton(text=r, callback_data=f"reg_{r}"))
    b.adjust(2)
    return b.as_markup()

def order_options_kb(selected=[]):
    b = InlineKeyboardBuilder()
    ac_txt = "❄️ AC (Konditsioner) ✅" if "ac" in selected else "❄️ AC (Konditsioner)"
    trunk_txt = "📦 Katta yukxona ✅" if "trunk" in selected else "📦 Katta yukxona"
    b.add(types.InlineKeyboardButton(text=ac_txt, callback_data="orderopt_ac"))
    b.add(types.InlineKeyboardButton(text=trunk_txt, callback_data="orderopt_trunk"))
    b.add(types.InlineKeyboardButton(text="✅ Tayyor / Keyingisi", callback_data="orderopt_done"))
    b.adjust(1)
    return b.as_markup()
# --- AI HELPERS (Voice to Text) ---
import base64
import aiohttp
async def transcribe_voice(voice_buffer: bytes) -> str:
    """Gemini AI orqali ovozni matnga o'giradi."""
    if not GEMINI_API_KEY: return "⚠️ AI kaliti (GEMINI_API_KEY) o'rnatilmagan."
    encoded_audio = base64.b64encode(voice_buffer).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{
            "parts": [
                {"text": "Ushbu ovozli xabarni matnga o'girib ber (O'zbek tilida). Faqat matnli javob qaytar."},
                {"inline_data": {"mime_type": "audio/ogg", "data": encoded_audio}}
            ]
        }]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"AI Transcription error: {e}")
    return "тЭМ Ovozni matnga o'girishda xatolik yuz berdi."
# --- BOT HANDLERS ---

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
@dp.message(Command("start"))
async def start_cmd(m: types.Message, state: FSMContext):
    u = await get_user_db(m.from_user.id)
    if not u:
        args = m.text.split()
        ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        await state.update_data(referred_by=ref_id, lang='uz')
        welcome_text = "👋 *Assalomu alaykum!* \nQishloq-Shahar Taksi botiga xush kelibsiz! ✨\n\n⚠️ *MUHIM:* Bot faqat vositachi hisoblanadi va nizolar uchun javobgar emas."
        choose_role = "Siz kimsiz? 👇"
        b = InlineKeyboardBuilder()
        b.add(types.InlineKeyboardButton(text="👨‍✈️ Haydovchiman", callback_data="role_driver"))
        b.add(types.InlineKeyboardButton(text="👤 Yo'lovchiman", callback_data="role_passenger"))
        await m.answer(f"{welcome_text}\n\n{choose_role}", parse_mode="Markdown", reply_markup=b.as_markup())
        await state.set_state(RegState.choosing_role)

    else:
                await m.answer(t(u[6], "welcome"), parse_mode="Markdown", reply_markup=await mkb(m.from_user.id))

@dp.message(F.text == "🚖 Haydovchi bo'lib ishlash")
async def become_driver(m: types.Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    u = await get_user_db(m.from_user.id)
    await state.update_data(role='driver', lang=lang, full_name=u[2])
    await m.answer(TEXTS[lang]["enter_car"])
    await state.set_state(RegState.entering_car)

async def set_lang(c: types.CallbackQuery, state: FSMContext):
    lang = c.data.split("_")[1]
    await state.update_data(lang=lang)
    tx = TEXTS[lang]
    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text=tx["role_driver"], callback_data="role_driver"))
    b.add(types.InlineKeyboardButton(text=tx["role_passenger"], callback_data="role_passenger"))
    await c.message.edit_text(f"{tx['welcome']}\n\n{tx['choose_role']}", parse_mode="Markdown", reply_markup=b.as_markup())
    await state.set_state(RegState.choosing_role)

@dp.callback_query(RegState.choosing_role)
async def set_role(c: types.CallbackQuery, state: FSMContext):
    role = c.data.split("_")[1]
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    await state.update_data(role=role)
    if role == 'passenger':
        # Skip name for passenger, go straight to phone
        b = ReplyKeyboardBuilder()
        b.row(types.KeyboardButton(text=TEXTS[lang]["enter_phone"], request_contact=True))
        await c.message.answer(TEXTS[lang]["enter_phone"], reply_markup=b.as_markup(resize_keyboard=True))
        await state.set_state(RegState.entering_phone)
    else:
        await c.message.edit_text(TEXTS[lang]["enter_name"])
        await state.set_state(RegState.entering_name)
@dp.message(RegState.entering_name)
async def reg_name(m: types.Message, state: FSMContext):
    await state.update_data(full_name=m.text)
    data = await state.get_data()
    lang = data['lang']
    if data['role'] == 'driver':
        await m.answer(TEXTS[lang]["enter_car"])
        await state.set_state(RegState.entering_car)
    else:
        b = ReplyKeyboardBuilder()
        b.row(types.KeyboardButton(text=TEXTS[lang]["enter_phone"], request_contact=True))
        await m.answer(TEXTS[lang]["enter_phone"], reply_markup=b.as_markup(resize_keyboard=True))
        await state.set_state(RegState.entering_phone)
@dp.message(RegState.entering_car)
async def reg_car(m: types.Message, state: FSMContext):
    await state.update_data(car_model=m.text)
    data = await state.get_data()
    await m.answer(TEXTS[data['lang']]["enter_number"])
    await state.set_state(RegState.entering_number)
@dp.message(RegState.entering_number)
async def reg_num(m: types.Message, state: FSMContext):
    await state.update_data(car_number=m.text)
    data = await state.get_data()
    await m.answer(TEXTS[data['lang']]["select_route_from"], reply_markup=reg_regions_kb())
    await state.set_state(RegState.selecting_route_from)
@dp.callback_query(RegState.selecting_route_from)
async def reg_r_from(c: types.CallbackQuery, state: FSMContext):
    reg = c.data.split("_")[1]
    await state.update_data(route_from=reg)
    data = await state.get_data()
    await c.message.edit_text(TEXTS[data['lang']]["select_route_to"], reply_markup=reg_regions_kb())
    await state.set_state(RegState.selecting_route_to)
@dp.callback_query(RegState.selecting_route_to)
async def reg_r_to(c: types.CallbackQuery, state: FSMContext):
    reg = c.data.split("_")[1]
    await state.update_data(route_to=reg)
    data = await state.get_data()
    await c.message.answer(TEXTS[data['lang']]["select_region"], reply_markup=reg_regions_kb())
    await state.set_state(RegState.selecting_region)
@dp.callback_query(RegState.selecting_region)
async def reg_final_reg(c: types.CallbackQuery, state: FSMContext):
    reg = c.data.split("_")[1]
    await state.update_data(region=reg)
    data = await state.get_data()
    if data['role'] == 'driver':
        b = InlineKeyboardBuilder()
        b.add(types.InlineKeyboardButton(text="тЭДя╕П AC (Konditsioner)", callback_data="feat_ac"))
        b.add(types.InlineKeyboardButton(text="ЁЯУж Katta yukxona", callback_data="feat_trunk"))
        b.add(types.InlineKeyboardButton(text="тЬЕ Tayyor", callback_data="feat_done"))
        b.adjust(1)
        await c.message.edit_text("Mashinangizda qo'shimcha imkoniyatlar bormi?", reply_markup=b.as_markup())
        await state.set_state(RegState.selecting_car_features)
    else:
        b = ReplyKeyboardBuilder()
        b.row(types.KeyboardButton(text=TEXTS[data['lang']]["enter_phone"], request_contact=True))
        await c.message.answer(TEXTS[data['lang']]["enter_phone"], reply_markup=b.as_markup(resize_keyboard=True))
        await state.set_state(RegState.entering_phone)
@dp.callback_query(RegState.selecting_car_features)
async def reg_features(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    feats = data.get('features', [])
    if c.data == "feat_done":
        b = ReplyKeyboardBuilder()
        b.row(types.KeyboardButton(text=TEXTS[data['lang']]["enter_phone"], request_contact=True))
        await c.message.answer(TEXTS[data['lang']]["enter_phone"], reply_markup=b.as_markup(resize_keyboard=True))
        await state.set_state(RegState.entering_phone)
    else:
        feat = c.data.split("_")[1]
        if feat not in feats: feats.append(feat)
        await state.update_data(features=feats)
        await c.answer(f"тЬЕ {feat} qo'shildi")
@dp.message(RegState.entering_phone, F.contact)
async def reg_finish(m: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        uid = m.from_user.id
        now = datetime.now().strftime("%Y-%m-%d")
        ref_by = data.get('referred_by')
        lang = data.get('lang', 'uz')
        role = data.get('role', 'passenger')
        full_name = data.get('full_name', f"User_{uid}" if role == 'passenger' else 'Driver')
        
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("INSERT OR REPLACE INTO users (user_id, username, full_name, phone, role, reg_date, lang, referred_by) VALUES (?,?,?,?,?,?,?,?)", 
                             (uid, m.from_user.username, full_name, m.contact.phone_number, role, now, lang, ref_by))
            if role == 'driver':
                trial = (datetime.now() + timedelta(days=TRIAL_DAYS)).strftime("%Y-%m-%d %H:%M")
                feats = data.get('features', [])
                ac = 1 if 'ac' in feats else 0
                trunk = 1 if 'trunk' in feats else 0
                await db.execute("INSERT OR REPLACE INTO drivers (user_id, car_model, car_number, region, route_from, route_to, trial_ends_at, has_ac, large_trunk) VALUES (?,?,?,?,?,?,?,?,?)",
                                 (uid, data.get('car_model','-'), data.get('car_number','-'), data.get('region','-'), data.get('route_from','-'), data.get('route_to','-'), trial, ac, trunk))
            if ref_by:
                await db.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (ref_by,))
            await db.commit()
            
        if role == "driver":
            msg = """🎉 Muvaffaqiyatli ro'yxatdan o'tdingiz!
🎁 Sizga haydovchi sifatida 30 kunlik bepul sinov muddati berildi!"""
        else:
            msg = """🎉 Muvaffaqiyatli ro'yxatdan o'tdingiz!
🚀 Botdan umrbod bepul foydalanishingiz mumkin. Safarni boshlash uchun quyidagi menyudan foydalaning!"""
            
        await m.answer(msg, reply_markup=await mkb(uid))
        await state.clear()
    except Exception as e:
        logger.error(f"Error in reg_finish: {e}")
        await m.answer("❌ Ro'yxatdan o'tishda xatolik yuz berdi. Iltimos qayta /start bosing.")


# --- PASSENGER ORDER & PRICE CALC ---
@dp.message(F.text.in_([TEXTS["uz"]["main_order"], TEXTS["ru"]["main_order"], TEXTS["en"]["main_order"]]))
async def order_start(m: types.Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    await m.answer(TEXTS[lang]["select_route_from"], reply_markup=reg_regions_kb())
    await state.set_state(OrderState.choosing_origin)
@dp.callback_query(OrderState.choosing_origin)
async def order_origin(c: types.CallbackQuery, state: FSMContext):
    reg = c.data.split("_")[1]
    await state.update_data(origin=reg)
    lang = await get_lang(c.from_user.id)
    await c.message.edit_text(TEXTS[lang]["select_route_to"], reply_markup=reg_regions_kb())
    await state.set_state(OrderState.choosing_destination)
@dp.callback_query(OrderState.choosing_destination)
async def order_dest(c: types.CallbackQuery, state: FSMContext):
    reg = c.data.split("_")[1]
    data = await state.get_data()
    lang = await get_lang(c.from_user.id)
    await state.update_data(destination=reg)
    # Calculate suggested price
    c1 = REGION_COORDS.get(data['origin'], (41, 69))
    c2 = REGION_COORDS.get(reg, (41, 69))
    dist = haversine(c1, c2)
    if dist >= 50:
        s_price = int(5000 + dist * 1500)
        s_price = round(s_price, -3)
        await state.update_data(s_price=s_price)
    else:
        await state.update_data(s_price=None)
    
    await c.message.edit_text(TEXTS[lang].get("choose_options", "Qo'shimcha imkoniyatlar kerakmi?"), reply_markup=order_options_kb())
    await state.set_state(OrderState.choosing_filters)

@dp.callback_query(OrderState.choosing_filters)
async def process_order_filters(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    opts = data.get('options', [])
    lang = await get_lang(c.from_user.id)
    if c.data == "orderopt_done":
        b = ReplyKeyboardBuilder()
        btn_text = TEXTS[lang].get("send_location", "📍 Joylashuvni yuborish")
        b.row(types.KeyboardButton(text=btn_text, request_location=True))
        await c.message.answer(TEXTS[lang]["ask_location"], reply_markup=b.as_markup(resize_keyboard=True))
        await state.set_state(OrderState.entering_location)
        await c.answer()
    else:
        opt = c.data.split("_")[1]
        if opt in opts: opts.remove(opt)
        else: opts.append(opt)
        await state.update_data(options=opts)
        await c.message.edit_reply_markup(reply_markup=order_options_kb(opts))
        await c.answer()
@dp.message(OrderState.entering_location, F.location)
async def order_loc(m: types.Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    data = await state.get_data()
    await state.update_data(lat=m.location.latitude, lon=m.location.longitude)
    price_val = data.get('s_price')
    if price_val:
        txt = TEXTS[lang]["suggested_price"].format(price=price_val)
    else:
        txt = "💰 O'z narxingizni yozing:"
    await m.answer(txt, reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrderState.entering_price)
@dp.message(OrderState.entering_price)
async def order_finish(m: types.Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    data = await state.get_data()
    u = await get_user_db(m.from_user.id)
    now = datetime.now().strftime("%H:%M")
    opts = data.get('options', [])
    ac = 1 if 'ac' in opts else 0
    trunk = 1 if 'trunk' in opts else 0
    
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT INTO orders (user_id, origin, destination, price, created_at, lat, lon, has_ac, large_trunk) VALUES (?,?,?,?,?,?,?,?,?)",
                         (m.from_user.id, data['origin'], data['destination'], m.text, now, data['lat'], data['lon'], ac, trunk))
        await db.commit()
        order_id = (await (await db.execute("SELECT last_insert_rowid()")).fetchone())[0]

    # Notify drivers
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("""SELECT user_id FROM drivers 
                                 WHERE status=1 AND trial_ends_at > ? 
                                 AND ((route_from=? AND route_to=?) OR (route_from=? AND route_to=?))
                                 AND has_ac >= ? AND large_trunk >= ?""",
                              (now_str, data['origin'], data['destination'], data['destination'], data['origin'], ac, trunk)) as cur:
            drivers = await cur.fetchall()
    
    link = f"https://www.google.com/maps?q={data['lat']},{data['lon']}"
    feat_str = ""
    if ac: feat_str += "\n❄️ AC: Bor"
    if trunk: feat_str += "\n📦 Yukxona: Katta"
    
    msg = f"📢 *YANGI BUYURTMA!* ({data['origin']} -> {data['destination']})\n💰 Narxi: {m.text}{feat_str}\n👤 {u[2]} ({u[3]})\n📍 [Xarita]({link})"
    
    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept_order_{order_id}"))
    b.add(types.InlineKeyboardButton(text="💰 Narx taklif qilish", callback_data=f"counter_offer_{order_id}"))
    b.adjust(2)
    
    for d in drivers:
        try: await bot.send_message(d[0], msg, parse_mode="Markdown", reply_markup=b.as_markup())
        except: pass
    await m.answer(TEXTS[lang]["order_sent_all"], reply_markup=await mkb(m.from_user.id))
    await state.clear()
# --- DRIVER PANEL ---
@dp.message(F.text.in_([TEXTS["uz"]["main_profile"], TEXTS["ru"]["main_profile"], TEXTS["en"]["main_profile"]]))
async def show_profile(m: types.Message):
    uid = m.from_user.id
    u = await get_user_db(uid)
    lang = await get_lang(uid)
    if not u: return
    tx = TEXTS[lang]
    role_name = "🚕 Haydovchi" if u[4] == 'driver' else "👤 Yo'lovchi"
    
    profile_text = (
        f"👤 *{tx['main_profile']}*\n\n"
        f"🆔 ID: `{u[0]}`\n"
        f"🎭 Rol: *{role_name}*\n"
        f"👤 Ism: *{u[2]}*\n"
        f"📞 Tel: *{u[3]}*\n"
        f"👥 Referallar: {u[9]} ta do'st\n"
        f"🔗 Havola: `https://t.me/{(await bot.get_me()).username}?start={u[0]}`"
    )
    
    b = InlineKeyboardBuilder()
    if u[4] == 'driver':
        b.add(types.InlineKeyboardButton(text="👤 Yo'lovchilikka o'tish", callback_data="switch_role_passenger"))
    else:
        b.add(types.InlineKeyboardButton(text="🚕 Haydovchilikka o'tish", callback_data="switch_role_driver"))
    
    b.add(types.InlineKeyboardButton(text="🆘 SOS Kontaktni sozlash", callback_data="set_sos_contact"))
    b.adjust(1)
    await m.answer(profile_text, parse_mode="Markdown", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("switch_role_"))
async def switch_role(c: types.CallbackQuery, state: FSMContext):
    target = c.data.split("_")[2]
    uid = c.from_user.id
    lang = await get_lang(uid)
    if target == "driver":
        d = await get_driver_db(uid)
        if d:
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("UPDATE users SET role='driver' WHERE user_id=?", (uid,))
                await db.commit()
            await c.message.edit_text("✅ Siz haydovchi rejimiga o'tdingiz!", reply_markup=None)
            await c.message.answer("Xush kelibsiz haydovchi!", reply_markup=await mkb(uid))
        else:
            await c.message.edit_text("📝 Haydovchi sifatda ro'yxatdan o'tishingiz kerak.")
            await state.update_data(role="driver", lang=lang)
            await c.message.answer(TEXTS[lang]["enter_car"])
            await state.set_state(RegState.entering_car)
    else:
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("UPDATE users SET role='passenger' WHERE user_id=?", (uid,))
            await db.commit()
        await c.message.edit_text("✅ Siz yo'lovchi rejimiga o'tdingiz!", reply_markup=None)
        await c.message.answer("Xush kelibsiz yo'lovchi!", reply_markup=await mkb(uid))
    await c.answer()

@dp.message(F.text.in_([TEXTS["uz"]["main_driver"], TEXTS["ru"]["main_driver"], TEXTS["en"]["main_driver"]]))
async def driver_panel(m: types.Message):
    lang = await get_lang(m.from_user.id)
    driver = await get_driver_db(m.from_user.id)
    if not driver: return
    tx = TEXTS[lang]
    status_text = "🟢 Aktiv" if driver[6] == 1 else "🔴 Passiv"
    panel_text = (
        f"👨‍✈️ *{tx['main_driver']}*\n\n"
        f"🚘 *Mashina:* {driver[1]} ({driver[2]})\n"
        f"📍 *Yonalish:* {driver[4]} ↔️ {driver[5]}\n"
        f"📊 *Status:* {status_text}\n"
        f"📅 *Obuna muddati:* {driver[8]}\n"
        f"💰 *Balans:* {driver[7]:,} so'm"
    )
    b = InlineKeyboardBuilder()
    if driver[6] == 0:
        b.add(types.InlineKeyboardButton(text="✅ Go Online", callback_data="set_active"))
    else:
        b.add(types.InlineKeyboardButton(text="❌ Go Offline", callback_data="set_passive"))
    b.add(types.InlineKeyboardButton(text="🔄 Yo'nalishni o'zgartirish", callback_data="change_route"))
    b.add(types.InlineKeyboardButton(text="📍 Joylashuvni yangilash", callback_data="update_loc"))
    b.adjust(1)
    await m.answer(panel_text, parse_mode="Markdown", reply_markup=b.as_markup())
@dp.callback_query(F.data == "set_active")
async def make_active(c: types.CallbackQuery):
    d = await get_driver_db(c.from_user.id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if d[8] < now:
        await c.answer("тЭМ Obuna muddati tugagan! Iltimos, balansni to'ldiring.", show_alert=True)
        return
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE drivers SET status = 1 WHERE user_id = ?", (c.from_user.id,))
        await db.commit()
    await c.message.edit_text("тЬЕ Siz hozir ONLAYNSIZ! Yo'nalishingizdagi buyurtmalar sizga yuboriladi.")
    await c.answer()
@dp.callback_query(F.data == "set_passive")
async def make_passive(c: types.CallbackQuery):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE drivers SET status = 0 WHERE user_id = ?", (c.from_user.id,))
        await db.commit()
    await c.message.edit_text("🛑 Siz hozir OFFLINESIZ.")
    await c.answer()

@dp.callback_query(F.data == "update_loc")
async def start_update_loc(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("📍 Joriy joylashuvni yuboring:", reply_markup=ReplyKeyboardBuilder().row(types.KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)).as_markup(resize_keyboard=True))
    await state.set_state(DriverState.updating_loc)
    await c.answer()

@dp.message(DriverState.updating_loc, F.location)
async def process_update_loc(m: types.Message, state: FSMContext):
    uid = m.from_user.id
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE drivers SET lat = ?, lon = ? WHERE user_id = ?", (m.location.latitude, m.location.longitude, uid))
        await db.commit()
    await m.answer("✅ Joylashuvingiz yangilandi!", reply_markup=await mkb(uid))
    await state.clear()

@dp.message(F.text == "📜 Mening buyurtmalarim")
async def show_orders_history(m: types.Message):
    uid = m.from_user.id
    u = await get_user_db(uid)
    role = u[4]
    async with aiosqlite.connect(DB_FILE) as db:
        if role == 'driver':
            cur = await db.execute("SELECT id, origin, destination, price, status, created_at FROM orders WHERE driver_id = ? ORDER BY id DESC LIMIT 5", (uid,))
        else:
            cur = await db.execute("SELECT id, origin, destination, price, status, created_at FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 5", (uid,))
        orders = await cur.fetchall()
    
    if not orders:
        await m.answer("📭 Hozircha buyurtmalar mavjud emas.")
        return
    
    text = "📜 *OXIRGI BUYURTMALARINGIZ:*\n\n"
    for o in orders:
        status_emoji = "✅" if o[4] == 'accepted' else "⏳" if o[4] == 'open' else "❌"
        text += f"{status_emoji} *#{o[0]}* | {o[1]} ➔ {o[2]}\n💳 {o[3]} so'm | {o[5]}\n\n"
    
    await m.answer(text, parse_mode="Markdown")
@dp.message(F.text.in_([TEXTS["uz"]["main_balance"], TEXTS["ru"]["main_balance"], TEXTS["en"]["main_balance"]]))
async def show_balance(m: types.Message):
    lang = await get_lang(m.from_user.id)
    d = await get_driver_db(m.from_user.id)
    if not d: return
    txt = f"💰 {TEXTS[lang]['main_balance']}: {d[7]} UZS\nЁЯУЕ Expiry: {d[8]}"
    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text=TEXTS[lang]["top_up"], callback_data="top_up"))
    await m.answer(txt, reply_markup=b.as_markup())
@dp.callback_query(F.data == "top_up")
async def process_top_up(c: types.CallbackQuery):
    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text="1 kun (2 000)", callback_data="pay_1"))
    b.add(types.InlineKeyboardButton(text="7 kun (14 000)", callback_data="pay_7"))
    b.add(types.InlineKeyboardButton(text="30 kun (60 000)", callback_data="pay_30"))
    await c.message.edit_text("Obuna muddatini tanlang:", reply_markup=b.as_markup())
@dp.callback_query(F.data.startswith("pay_"))
async def send_invoice(c: types.CallbackQuery):
    days = int(c.data.split("_")[1])
    price = days * DAILY_FEE
    await bot.send_invoice(
        c.from_user.id, title="Taxi Subscription", description=f"{days} kunlik obuna",
        payload=f"sub_{days}", provider_token=PAYMENT_TOKEN, currency="UZS",
        prices=[types.LabeledPrice(label=f"{days} kunlik", amount=price * 100)]
    )
@dp.pre_checkout_query()
async def pre_checkout(pcq: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pcq.id, ok=True)
@dp.message(F.successful_payment)
async def success_pay(m: types.Message):
    days = int(m.successful_payment.invoice_payload.split("_")[1])
    d = await get_driver_db(m.from_user.id)
    now = datetime.now()
    current_expiry = datetime.strptime(d[8], "%Y-%m-%d %H:%M") if d[8] > now.strftime("%Y-%m-%d %H:%M") else now
    new_expiry = (current_expiry + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE drivers SET trial_ends_at = ?, balance = balance + ? WHERE user_id = ?", 
                         (new_expiry, days * DAILY_FEE, m.from_user.id))
        await db.commit()
    await m.answer(f"тЬЕ Tolov qabul qilindi! Yangi muddat: {new_expiry}")
# --- SOS ---
@dp.callback_query(F.data == "set_sos_contact")
async def start_set_sos(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Yaqiningizning Telegram ID raqamini (sonlarni) yuboring. \n\nEslatma: Yaqiningiz avval ushbu botga kirishi (Start bosishi) kerak!")
    await state.set_state(SetSOS.entering_id)
    await c.answer()
@dp.message(SetSOS.entering_id)
async def process_set_sos(m: types.Message, state: FSMContext):
    if not m.text.isdigit():
        await m.answer("Iltimos, faqat ID raqamini kiriting!")
        return
    sos_id = int(m.text)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE users SET sos_contact_id = ? WHERE user_id = ?", (sos_id, m.from_user.id))
        await db.commit()
    await m.answer(f"тЬЕ SOS Kontakt muvaffaqiyatli saqlandi! \nID: `{sos_id}`", reply_markup=await mkb(m.from_user.id))
    await state.clear()
@dp.message(F.text.in_([TEXTS["uz"]["main_sos"], TEXTS["ru"]["main_sos"], TEXTS["en"]["main_sos"]]))
async def sos_cmd(m: types.Message):
    lang = await get_lang(m.from_user.id)
    u = await get_user_db(m.from_user.id)
    # We ask for current location for SOS
    b = ReplyKeyboardBuilder()
    b.row(types.KeyboardButton(text="🆘 SEND SOS LOCATION", request_location=True))
    await m.answer("🆘 Please send your live location for SOS!", reply_markup=b.as_markup(resize_keyboard=True))
@dp.message(F.voice)
async def handle_voice_msg(message: types.Message, state: FSMContext):
    lang = await get_lang(message.from_user.id)
    u = await get_user_db(message.from_user.id)
    if u[4] != 'passenger':
        msg = await message.answer("тП│ _Ovoz tahlil qilinmoqda..._")
        voice = await bot.get_file(message.voice.file_id)
        voice_buffer = await bot.download_file(voice.file_path)
        text = await transcribe_voice(voice_buffer.read())
        await msg.edit_text(f"ЁЯОд *Sizning xabaringiz:* \n\n{text}", parse_mode="Markdown")
        return
    # Passenger Voice-to-Order
    msg = await message.answer("🤖 _AI Buyurtmani tahlil qilmoqda..._")
    voice = await bot.get_file(message.voice.file_id)
    voice_buffer = await bot.download_file(voice.file_path)
    audio_data = voice_buffer.read()
    # Special prompt for ordering
    prompt = """Ushbu ovozli xabardan (taksi buyurtmasi) 'qayerdan', 'qayerga' va 'narx' ma'lumotlarini ajratib ol.
    Javobni FAQAT JSON formatida ber: {"from": "...", "to": "...", "price": "...", "ac": 0/1, "trunk": 0/1}. 
    Agar ma'lumot yo'q bo'lsa null yoz."""
    encoded_audio = base64.b64encode(audio_data).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "audio/ogg", "data": encoded_audio}}]}]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                ai_text = data["candidates"][0]["content"]["parts"][0]["text"]
                # Clean JSON
                ai_text = ai_text.replace("```json", "").replace("```", "").strip()
                order_info = json.loads(ai_text)
                if order_info.get("from") and order_info.get("to"):
                    res_text = f"📍 *Qayerdan:* {order_info['from']}\n🏁 *Qayerga:* {order_info['to']}\n💰 *Narx:* {order_info['price']}\n\nUshbu buyurtmani tasdiqlaysizmi?"
                    b = InlineKeyboardBuilder()
                    # Store info in callback
                    b.add(types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="ai_confirm"))
                    b.add(types.InlineKeyboardButton(text="❌ Rad etish", callback_data="ai_cancel"))
                    await state.update_data(ai_order=order_info)
                    await msg.edit_text(res_text, parse_mode="Markdown", reply_markup=b.as_markup())
                else:
                    await msg.edit_text("😕 Buyurtma ma'lumotlarini tushunolmadim. Iltimos, aniqroq ayting yoki yozing.")
    except:
        await msg.edit_text("❌ Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")
@dp.message(F.location, ~F.text) # Catching SOS location outside of order FSM
async def handle_sos_loc(m: types.Message):
    lang = await get_lang(m.from_user.id)
    u = await get_user_db(m.from_user.id)
    link = f"https://www.google.com/maps?q={m.location.latitude},{m.location.longitude}"
    sos_msg = TEXTS["en"]["sos_sent"].format(user=u[2], link=link)
    # Send to ADMIN
    await bot.send_message(ADMIN_ID, sos_msg, parse_mode="Markdown")
    # Send to Relative (SOS Contact)
    if u[7]: # sos_contact_id is index 7 (starting from 0)
        try:
            await bot.send_message(u[7], f"ЁЯФ┤ *SOS:* {u[2]} yordam so'ramoqda!\n[Xaritada ko'rish]({link})", parse_mode="Markdown")
        except:
            pass # Could not send if relative didn't start the bot
    await m.answer("ЁЯЪи SOS sent to Admin! Stay safe.", reply_markup=await mkb(m.from_user.id))
# --- SUPPORT ---
@dp.message(F.text.in_([TEXTS["uz"]["main_support"], TEXTS["ru"]["main_support"], TEXTS["en"]["main_support"]]))
async def support_start(m: types.Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    await m.answer(TEXTS[lang]["support_ask"])
    await state.set_state(SupportState.entering_msg)
@dp.message(SupportState.entering_msg)
async def feedback_submit(m: types.Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    u = await get_user_db(m.from_user.id)
    # Forward original message to admin
    caption = f"📩 *NEW FEEDBACK!*\n👤 {u[2]} ({u[3]})\nRole: {u[4]}"
    await bot.send_message(ADMIN_ID, caption, parse_mode="Markdown")
    await bot.copy_message(ADMIN_ID, m.from_user.id, m.message_id)
    await m.answer(TEXTS[lang]["support_sent"], reply_markup=await mkb(m.from_user.id))
    await state.clear()
# --- CALLBACKS FOR ORDERS ---
@dp.callback_query(F.data.startswith("counter_offer_"))
async def start_counter(c: types.CallbackQuery, state: FSMContext):
    order_id = c.data.split("_")[2]
    await state.update_data(c_order_id=order_id)
    await c.message.answer("O'z narxingizni yozing:")
    await state.set_state(CounterOffer.entering_price)
    await c.answer()
@dp.message(CounterOffer.entering_price)
async def process_counter(m: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data['c_order_id']
    price = m.text
    async with aiosqlite.connect(DB_FILE) as db:
        cur = await db.execute("SELECT user_id FROM orders WHERE id=?", (order_id,))
        order = await cur.fetchone()
    
    driver = await get_driver_db(m.from_user.id)
    u_driver = await get_user_db(m.from_user.id)
    
    b = InlineKeyboardBuilder()
    # Format: accept_counter_{order_id}_{driver_id}_{price}
    b.add(types.InlineKeyboardButton(text="✅ Roziman", callback_data=f"accept_counter_{order_id}_{m.from_user.id}_{price}"))
    b.add(types.InlineKeyboardButton(text="❌ Yo'q", callback_data=f"reject_counter_{m.from_user.id}_{order_id}"))
    b.adjust(1)

    msg = (
        f"💰 *YANGI NARX TAKLIFI!*\n\n"
        f"🚕 Haydovchi: *{u_driver[2]}*\n"
        f"🚘 Mashina: *{driver[1]} ({driver[2]})*\n"
        f"💵 Taklif qilingan narx: *{price} so'm*\n\n"
        f"Ushbu narxga rozi bo'lasizmi?"
    )
    await bot.send_message(order[0], msg, parse_mode="Markdown", reply_markup=b.as_markup())
    await m.answer("✅ Sizning narxingiz yo'lovchiga yuborildi.")
    await state.clear()
# --- ADMIN COMMANDS ---
@dp.message(Command("admin"))
async def admin_cmd(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect(DB_FILE) as db:
        u_count = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        d_count = await (await db.execute("SELECT COUNT(*) FROM drivers")).fetchone()
        o_count = await (await db.execute("SELECT COUNT(*) FROM orders WHERE status='open'")).fetchone()
    text = (
        "👨‍✈️ *ADMIN PANEL*\n\n"
        f"Foydalanuvchilar: {u_count[0]}\n"
        f"Haydovchilar: {d_count[0]}\n"
        f"Ochiq buyurtmalar: {o_count[0]}\n\n"
        "/send - Reklama yuborish\n"
        "/orders - Buyurtmalar"
    )
    await m.answer(text, parse_mode="Markdown")
@dp.message(Command("send"))
async def admin_send(m: types.Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    await m.answer("Xabar matnini yuboring:")
    await state.set_state(AdminState.entering_ad)
@dp.message(AdminState.entering_ad)
async def process_ad(m: types.Message, state: FSMContext):
    await state.update_data(ad_msg=m.message_id)
    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text="тЬЕ Yuborish", callback_data="confirm_ad"))
    await m.answer("Yuborishni tasdiqlaysizmi?", reply_markup=b.as_markup())
    await state.set_state(AdminState.confirm_ad)
@dp.callback_query(AdminState.confirm_ad, F.data == "confirm_ad")
async def confirm_ad(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect(DB_FILE) as db:
        users = await (await db.execute("SELECT user_id FROM users")).fetchall()
    for uid in users:
        try: await bot.copy_message(uid[0], c.from_user.id, data['ad_msg'])
        except: pass
    await c.message.edit_text("тЬЕ Xabar hamma foydalanuvchilarga yuborildi.")
    await state.clear()
# --- BACKGROUND TASKS ---
async def subscription_reminder_loop():
    while True:
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT user_id, trial_ends_at FROM drivers WHERE trial_ends_at LIKE ?", (tomorrow[:13] + "%",)) as cur:
                expiring = await cur.fetchall()
        for uid, date in expiring:
            try: await bot.send_message(uid, f"⚠️ *Eslatma:* Obuna muddatingiz ertaga ({date}) tugaydi. Balansni to'ldirishni unutmang!")
            except: pass
        await asyncio.sleep(3600)
# --- WEB SERVER (Map and JSON API) ---
async def handle_map(req):
    origin = req.query.get('origin', 'Toshkent')
    dest = req.query.get('dest', '')
    lat = req.query.get('lat', '41.3110')
    lon = req.query.get('lon', '69.2405')
    
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(base_dir, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
            return web.Response(text=html, content_type='text/html')
    except Exception as e:
        logger.error(f"Error reading index.html: {e}")
        return web.Response(text="<h1>404 - WebApp Page Not Found</h1>", content_type='text/html', status=404)
async def handle_json(req):
    origin = req.query.get('origin', '')
    dest = req.query.get('dest', '')
    async with aiosqlite.connect(DB_FILE) as db:
        query = "SELECT u.full_name, u.phone, d.car_model, d.lat, d.lon FROM drivers d JOIN users u ON d.user_id=u.user_id WHERE d.status=1"
        args = []
        if origin and dest:
            query += " AND ((d.route_from=? AND d.route_to=?) OR (d.route_from=? AND d.route_to=?))"
            args = [origin, dest, dest, origin]
        elif origin:
            query += " AND (d.region=? OR d.route_from=? OR d.route_to=?)"
            args = [origin, origin, origin]
        async with db.execute(query, args) as cur:
            d = await cur.fetchall()
    data = [{"name": x[0], "phone": x[1], "car": x[2], "lat": x[3], "lon": x[4]} for x in d]
    return web.json_response(data)
# --- MAIN ---

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

async def main():
    await init_db()
    asyncio.create_task(subscription_reminder_loop())
    asyncio.create_task(keep_alive_loop())
    # Web server
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is online!") if r.method=="GET" else web.Response(status=405))
    app.router.add_get("/map", handle_map)
    app.router.add_get("/drivers_json", handle_json)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8081))).start()
    logger.info("INTERNATIONAL TAXI BOT STARTED!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
@dp.callback_query(F.data == "ai_confirm")
async def ai_confirm(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order = data.get('ai_order')
    if not order: return
    now = datetime.now().strftime("%H:%M")
    u = await get_user_db(c.from_user.id)
    ac = 1 if order.get('ac') else 0
    trunk = 1 if order.get('trunk') else 0
    
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT INTO orders (user_id, origin, destination, price, created_at, has_ac, large_trunk) VALUES (?,?,?,?,?,?,?)",
                         (c.from_user.id, order['from'], order['to'], order['price'], now, ac, trunk))
        await db.commit()
        order_id = (await (await db.execute("SELECT last_insert_rowid()")).fetchone())[0]

    # Find drivers
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("""SELECT user_id FROM drivers 
                                 WHERE status=1 AND trial_ends_at > ? 
                                 AND (region LIKE ? OR route_from LIKE ? OR route_to LIKE ?)
                                 AND has_ac >= ? AND large_trunk >= ?""",
                              (now_str, f"%{order['from']}%", f"%{order['from']}%", f"%{order['from']}%", ac, trunk)) as cur:
            drivers = await cur.fetchall()
            
    feat_str = ""
    if ac: feat_str += "\n❄️ AC: Ha"
    if trunk: feat_str += "\n📦 Yukxona: Katta"
    
    msg = f"📢 *AI BUYURTMA!* \n📍 {order['from']} -> {order['to']}\n💰 Narxi: {order['price']}{feat_str}\n👤 {u[2]} ({u[3]})"
    
    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept_order_{order_id}"))
    b.adjust(1)
    
    for d in drivers:
        try: await bot.send_message(d[0], msg, parse_mode="Markdown", reply_markup=b.as_markup())
        except: pass
    await c.message.edit_text("✅ AI Buyurtmangiz qabul qilindi va haydovchilarga yuborildi!")
    await c.message.answer("Asosiy menyu:", reply_markup=await mkb(c.from_user.id))
    await state.clear()
    await c.answer()

@dp.message(F.text.in_([TEXTS["uz"]["main_search"], TEXTS["ru"]["main_search"]]))
async def search_start(m: types.Message, state: FSMContext):
    await m.answer("Qaysi hududdan haydovchi qidirmoqdasiz?", reply_markup=reg_regions_kb())
    await state.set_state(OrderState.searching_driver)

@dp.callback_query(OrderState.searching_driver)
async def search_perform(c: types.CallbackQuery, state: FSMContext):
    reg = c.data.split("_")[1]
    url = f"{RENDER_URL}/map?origin={reg}"
    b = InlineKeyboardBuilder()
    b.add(types.InlineKeyboardButton(text="🗺 Xaritada ko'rish", web_app=WebAppInfo(url=url)))
    await c.message.edit_text(f"📍 *{reg}* hududidagi faol haydovchilarni xaritada ko'ring:", parse_mode="Markdown", reply_markup=b.as_markup())
    await state.clear()
    await c.answer()
@dp.callback_query(F.data == "ai_cancel")
async def ai_cancel(c: types.CallbackQuery, state: FSMContext):
    await c.message.edit_text("❌ Buyurtma bekor qilindi.")
    await state.clear()
    await c.answer()
@dp.callback_query(F.data.startswith("accept_order_"))
async def accept_order(c: types.CallbackQuery):
    order_id = c.data.split("_")[2]
    driver_id = c.from_user.id
    
    async with aiosqlite.connect(DB_FILE) as db:
        # Statusni yangilash (faqat 'open' bo'lsa)
        cur = await db.execute("UPDATE orders SET status='accepted', driver_id=? WHERE id=? AND status='open'", (driver_id, order_id))
        await db.commit()
        
        if cur.rowcount == 0:
            await c.answer("❌ Bu buyurtmani boshqa haydovchi olib bo'lgan.", show_alert=True)
            await c.message.delete()
            return

        async with db.execute("SELECT user_id, price, origin, destination FROM orders WHERE id=?", (order_id,)) as cur_o:
            order = await cur_o.fetchone()

    passenger_id = order[0]
    u_pass = await get_user_db(passenger_id)
    u_driver = await get_user_db(driver_id)
    driver = await get_driver_db(driver_id)

    # Yo'lovchiga xabar
    msg_p = f"✅ *Haydovchi topildi!*\n\n🚕 Haydovchi: *{u_driver[2]}*\n📞 Tel: *{u_driver[3]}*\n🚘 Mashina: *{driver[1]} ({driver[2]})*\n💰 Narx: *{order[1]} so'm*"
    try: await bot.send_message(passenger_id, msg_p, parse_mode="Markdown")
    except: pass

    # Haydovchiga yo'lovchi raqami
    await c.message.edit_text(f"✅ Buyurtma qabul qilindi!\n\n👤 Yo'lovchi: *{u_pass[2]}*\n📞 Tel: *{u_pass[3]}*", parse_mode="Markdown")
    await c.answer("Muvaffaqiyatli qabul qildingiz!")

@dp.callback_query(F.data.startswith("accept_counter_"))
async def accept_counter(c: types.CallbackQuery):
    # format: accept_counter_{order_id}_{driver_id}_{price}
    parts = c.data.split("_")
    order_id, driver_id, price = parts[2], parts[3], parts[4]
    
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE orders SET status='accepted', driver_id=?, price=? WHERE id=?", (driver_id, price, order_id))
        await db.commit()

    u_pass = await get_user_db(c.from_user.id)
    u_driver = await get_user_db(driver_id)
    driver = await get_driver_db(driver_id)

    # Haydovchiga xabar
    try: await bot.send_message(driver_id, f"✅ Yo'lovchi narxingizga rozi bo'ldi (*{price}* so'm)!\n\n👤 Yo'lovchi: *{u_pass[2]}*\n📞 Tel: *{u_pass[3]}*", parse_mode="Markdown")
    except: pass

    await c.message.edit_text(f"✅ Haydovchi: *{u_driver[2]}*\n📞 Tel: *{u_driver[3]}*\n🚘 Mashina: *{driver[1]} ({driver[2]})*", parse_mode="Markdown")
    await c.answer("Tasdiqlandi!")

@dp.callback_query(F.data.startswith("reject_counter_"))
async def reject_counter(c: types.CallbackQuery):
    parts = c.data.split("_")
    driver_id = parts[2]
    # order_id optional: parts[3]
    try: await bot.send_message(driver_id, "❌ Yo'lovchi sizning narx taklifingizni rad etdi.")
    except: pass
    await c.message.edit_text("❌ Siz haydovchi taklifini rad etdingiz.")
    await c.answer()
if __name__ == "__main__":
    asyncio.run(main())
