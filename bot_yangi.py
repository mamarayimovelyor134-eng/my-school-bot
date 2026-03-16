import asyncio
import os
import logging
import random
import aiohttp
import base64
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import aiosqlite
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# --- CONFIG (Xavfsizlik uchun Environment Variables ishlatiladi) ---
TOKEN = os.environ.get("BOT_TOKEN", "8213419235:AAExR7swbjYl18CnGtJUzemWuw694-X2VMQ")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6363231317"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DB_FILE = "school_bot.db"


bot = Bot(token=TOKEN)
dp = Dispatcher()

# AI rejimidagi foydalanuvchilarni kuzatish
ai_sessions = set()

async def ask_gemini(question: str) -> str:
    """Bepul AI API ga savol yuboradi va javob qaytaradi."""
    # O'quvchilar ko'pincha namunadagi matnni nusxalab yuborishadi, shuni tozalaymiz
    clean_question = question.split("Masalan:")[-1].replace("•", "").strip()
    if not clean_question: clean_question = question

    # 1-usul: Pollinations AI (Eng barqaror va bepul)
    try:
        import urllib.parse
        system_prompt = (
            "Sen O'zbekiston maktab o'quvchilari uchun mehribon va bilimli Ustozsan. "
            "Qoidalar: 1. Murakkab narsalarni ham sodda, o'quvchi tilida tushuntirib ber. "
            "2. Faqat o'zbek tilida gaplash. 3. Reklama yoki havolalar berma. "
            "4. Har doim do'stona va rag'batlantiruvchi bo'l."
        )
        encoded_question = urllib.parse.quote(clean_question)
        encoded_system = urllib.parse.quote(system_prompt)
        url = f"https://text.pollinations.ai/{encoded_question}?model=openai&system={encoded_system}&json=false"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    response = await resp.text()
                    # Reklamani filtrlash
                    promo_keywords = ["t.me/", "http", "www.", "@", "obuna", "kanal"]
                    lines = response.split('\n')
                    clean_lines = [l for l in lines if not any(k in l.lower() for k in promo_keywords)]
                    return "\n".join(clean_lines).strip()
    except:
        pass # If Pollinations fails, it will fall through to the next method

    # Zuki fallback (Zuki free key echo model bo'lishi mumkin, shuning uchun 2-o'rinda)
    url = "https://api.zukijourney.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": "Bearer zuki-example-free"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Sen maktab o'quvchilari uchun yordamchi assistantsan."},
            {"role": "user", "content": clean_question}
        ],
        "max_tokens": 800
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = data["choices"][0]["message"]["content"]
                    # Reklamani filtrlash (AI ba'zan kanal yoki saytni reklama qilishi mumkin)
                    promo_keywords = ["t.me/", "http", "www.", "@", "obuna", "kanal"]
                    lines = response.split('\n')
                    clean_lines = [l for l in lines if not any(k in l.lower() for k in promo_keywords) or "google.com" in l or "wikipedia" in l]
                    return "\n".join(clean_lines).strip()
    except Exception as e:
        logging.error(f"ZukiJourney API error: {e}")
        
    return "❌ AI bilan bog'lanishda muammo bo'ldi. Iltimos, birozdan so'ng qayta urinib ko'ring."

async def ask_pollinations(question: str) -> str:
    """Pollinations AI - 100% bepul va ochiq"""
    import urllib.parse
    system = "Sen o'zbek maktab o'quvchilariga yordam beruvchi AI assistantsan. Faqat o'zbek tilida javob ber."
    encoded = urllib.parse.quote(question)
    url = f"https://text.pollinations.ai/{encoded}?model=openai&system={urllib.parse.quote(system)}&json=false"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    return await resp.text()
                else:
                    return "❌ AI javob bermadi. Internet yoki API muammosi bo'likshi mumkin."
    except Exception as e:
        return f"❌ Xatolik: {str(e)[:150]}"

async def solve_test_from_image(image_buffer: bytes) -> str:
    # 1-usul: Agar Google Gemini API Key bo'lsa
    if GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        img_b64 = base64.b64encode(image_buffer).decode("utf-8")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Sen O'zbekiston maktab o'quvchilari uchun yordamchisan. Ushbu rasmdagi test (yoki savol)ni tahlil qilib, to'g'ri javobini topib ber. Javobni qisqa, aniq va tushunarli o'zbek tilida ber."},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": img_b64
                            }
                        }
                    ]
                }
            ]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            pass # Agar Gemini ishlamasa, keyingi usulga o'tadi
    
    # 2-usul: ZukiJourney GPT-4o (Bepul)
    url = "https://api.zukijourney.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": "Bearer zuki-example-free"}
    img_b64 = base64.b64encode(image_buffer).decode("utf-8")
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Ushbu rasmdagi test yoki savolni qisqa va aniq qilib yechib ber, faqat o'zbek tilida yoz."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            }
        ],
        "max_tokens": 500
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=40)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
    except:
        pass
    
    return "❌ Rasmni o'qib bo'lmadi. Server javob bermayotgan bo'lishi mumkin."


async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, reg_date TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, task_text TEXT, remind_time TEXT, created_at TEXT, is_done BOOLEAN DEFAULT 0)")
        await db.commit()


# update_balance funksiyasi olib tashlandi

async def add_user(user_id, username):
    reg_date = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            if not await cursor.fetchone():
                await db.execute("INSERT INTO users (user_id, username, reg_date) VALUES (?, ?, ?)", 
                               (user_id, username, reg_date))
        await db.commit()


# --- MEGA DATA ---
# Eduportal uchun maxsus ID-lar (rasmiy sayt o'zgarishi sababli)
EDUPORTAL_IDS = {
    "1": "8", "2": "9", "3": "13", "4": "12", "5": "14", 
    "6": "6", "7": "7", "8": "17", "9": "18", "10": "11", "11": "19"
}

BOOKS_DATA = {
    str(i): [
        ("🏛 Kitob.uz (Asosiy)", f"https://kitob.uz/uz/library?genre=145&subgenre={145 + i}"),
        ("📘 Eduportal (Rasmiy)", f"http://eduportal.uz/Eduportal/batafsil1/{EDUPORTAL_IDS.get(str(i))}?menu=33"),
        ("📖 InfoEdu (Qo'shimcha)", f"https://infoedu.uz/category/darsliklar/{i}-sinf/"),
    ] for i in range(1, 12)
}


KREATIV_GAMES = {
    "Matematika": {
        "🧩 Domino o'yini": "Mavzu: Amallar bajarish. O'quvchilar misol javobini keyingi kartochka bilan moslaydi.",
        "🏁 Kimo'zar poygasi": "Mavzu: Og'zaki hisob. Doskada 2 ta guruh poygasi tashkil etiladi.",
        "🎡 Matematik Charkhpalak": "Mavzu: Ko'paytirish jadvali. Doira ichidagi sonlarni ko'paytirib tez aytish.",
        "💎 Wordwall: Matematika": "https://wordwall.net/uz/community/matematika"
    },
    "Ona tili": {
        "📝 So'z ichida so'z": "Mavzu: So'z yasalishi. Bitta uzun so'zdan yangi so'zlar yasash.",
        "🔍 Xatoni top": "Mavzu: Imlo qoidalari. Matndagi yashirilgan xatolarni tez topish.",
        "🏗 Gap qurish": "Mavzu: Sintaksis. Aralashib ketgan so'zlardan mantiqiy gap tuzish.",
        "💎 Wordwall: Ona tili": "https://wordwall.net/uz/community/ona-tili"
    },
    "Ingliz tili": {
        "🐝 Spelling Bee": "Mavzu: Vocabulary. So'zlarni harflab aytib berish musobaqasi.",
        "📸 Flashcards Battle": "Mavzu: Rasmli lug'at. Rasmni ko'rib inglizcha nomini tez aytish.",
        "🎭 Pantomima": "Mavzu: Verbs (Fe'llar). Harakatlarni ko'rsatib, inglizcha so'zni topish.",
        "💎 Wordwall: English": "https://wordwall.net/uz/community/english"
    },
    "Tarix": {
        "⏳ Sayohat": "Mavzu: Tarixiy sanalar. Sanani aytib, o'sha yili nima sodir bo'lganini topish.",
        "👑 Shaxslar": "Mavzu: Buyuk siymolar. Shaxs haqida ma'lumot beriladi, o'quvchi kimligini topadi.",
        "🗺 Xarita bilan ishlash": "Mavzu: Davlatlar. Xaritadan qadimiy davlatlar o'rnini ko'rsatish."
    },
    "Biologiya": {
        "🌿 Herbariy": "Mavzu: O'simliklar. Bargiga qarab o'simlik nomini topish.",
        "🧬 Zanjir": "Mavzu: Ekologiya. Oziq-ovqat zanjirini to'g'ri ketma-ketlikda tuzish.",
        "🔍 Yashirin a'zo": "Mavzu: Anatomiya. Inson a'zolarini vazifasiga qarab topish."
    },
    "Metodlar": {
        "💡 Aqliy hujum": "Dars boshida mavzuga oid tezkor savol-javoblar.",
        "🎨 Sinkveyn": "Mavzu yuzasidan 5 qatorli she'r tuzish orqali xulosa qilish.",
        "🧺 Toifa savati": "Ma'lumotlarni guruhlarga ajratib savatlarga solish."
    }
}

STARTUP_DATA = {
    "🚀 Startup nima?": "Startup — bu yangi, innovatsion g'oya asosida yaratilgan va tez rivojlanishga yo'naltirilgan biznes loyiha. Oddiy biznesdan farqi — u hal qilinmagan muammoni yangicha yechim bilan hal qiladi.",
    "💡 G'oya topish": "Atrofingizdagi muammolarga qarang. Odamlar nima qiynalayotganini topsangiz - bu startup uchun eng yaxshi g'oya hisoblanadi. Masalan: 'Maktabda ovqat buyurtma qilish ilovasi'.",
    "💻 IT darslari": "Startup yaratish uchun IT bilimlar zarur. IT-Park uz ko'plab bepul kurslarni taklif etadi: https://it-park.uz/",
    "🏆 Tanlovlar": "O'zbekistonda yoshlar uchun 'President Tech Award' va 'Startup Initiatives' kabi yirik tanlovlar mavjud. G'oliblar katta investitsiya yutib olishlari mumkin.",
    "🎓 Kelajak kasblari": "Dasturchi, Data Scientist, UI/UX Dizayner va Sun'iy intellekt muhandisi — bular eng istiqbolli yo'nalishlardir."
}



MOTIVATION_DATA = [
    "🌟 *Ilm — najotdir!* Har kuni 15 daqiqa kitob o'qish, bir yildan keyin sizni butunlay boshqa odamga aylantiradi.",
    "🚀 *Eng katta sarmoya — o'zingizga bo'lgan sarmoyadir.* Bugungi o'rganilgan bitta so'z — ertangi muvaffaqiyat poydevori.",
    "💡 *Xatolar — bu tajriba.* Yiqilishdan qo'rqmang, faqat o'sha yerda qolib ketishdan qo'rqing.",
    "📚 *Al-Xorazmiy, Ibn Sino va Beruniy ham sizdek o'quvchi bo'lishgan.* Ular dunyoni o'zgartirishgan, siz ham qila olasiz!",
    "🎓 *Bilim — bu superpower!* Uni hech kim sizdan tortib ololmaydi. O'qishdan to'xtamang.",
    "🌈 *Muvaffaqiyat siri — intizomda.* Kichik, lekin doimiy qadamlar ulkan cho'qqilarga olib chiqadi."
]




GAMES_DATA = [
    {"q": "Dunyoning eng baland cho'qqisi?", "a": "Everest", "o": ["Everest", "K2", "Monblan"]},
    {"q": "Inson tanasidagi eng katta organ?", "a": "Teri", "o": ["Jigar", "Yurak", "Teri"]},
    {"q": "Qaysi metal suyuq holatda bo'ladi?", "a": "Simob", "o": ["Simob", "Oltin", "Kumush"]},
    {"q": "O'zbekiston mustaqillik kuni?", "a": "1-sentabr", "o": ["31-avgust", "1-sentabr", "8-dekabr"]},
    {"q": "Koinotdagi eng issiq yulduz ranggi?", "a": "Moviy", "o": ["Qizil", "Sariq", "Moviy"]},
    {"q": "Suvning qaynash harorati?", "a": "100°C", "o": ["90°C", "100°C", "110°C"]},
    {"q": "Eng tez yuguradigan hayvon?", "a": "Gepard", "o": ["Arslon", "Gepard", "Zirafa"]},
    {"q": "Germanlar tomonidan rimliklarga yetkazib berilgan mahsulotlar qaysilar?", "a": "Teri va qahrabo", "o": ["Teri va qahrabo", "Bronza idishlar, taqinchoqlar", "Shisha, sopol buyumlar"]}
]

INTERNAL_ANSWERS = {
    "chsb_8_ona_tili_1": """
# 8-sinf Ona tili CHSB-1 Javoblari

### 1. Vazifa №1
**Savol:** Mustaqil so‘z turkumiga mansub bo‘lmagan so‘zlarni aniqlang.
1) nihoyat; 2) har kuni; 3) boyagi; 4) hayalla; 5) juda.
A) 1 va 5 | B) 1, 3, 5 | C) faqat 1 | D) 1, 3, 4
**Javob:** D (1, 3, 4)

### 2. Vazifa №2
**Savol:** Ijodiy-tavsifiy matn yuzasidan hukmlarni aniqlang.
1. Belgilar sanaladi (T)
2. So'z tanlash o'rni katta (T)
3. Ma'no butunligi bor (T)
4. Gap turlari farqi yo'q (N)
**Javob:** 1-to‘g‘ri, 2-to‘g‘ri, 3-to‘g‘ri, 4-noto‘g‘ri

### 3. Vazifa №3
**Savol:** So‘zlarni ma’nolari bilan moslashtiring.
1-madrasa (ta'lim); 2-viqor (salobat); 3-mulozim (xizmatchi); 4-horg'in (charchagan).
**Javob:** 1-a, 2-c, 3-d, 4-e

### 4. Vazifa №4
**Savol:** Qaysi qatorda so‘roq olmoshi qo‘llangan?
**Javob:** A) Siz kimlar bilan do‘stlashayotganingizga e’tiborli bo‘ling.

### 5. Vazifa №5
**Savol:** Sof ko‘makchi qo‘llangan gapni aniqlang.
**Javob:** Buvimdan tortib jiyanimgacha bu sirni bilgan.

### 6. Vazifa №6
**Savol:** Holatga taqlid so'z qo'llangan gap?
**Javob:** B) O‘q ovozini eshitgan qizaloqlar dag‘-dag‘ qaltiray boshladilar.

### 7. Vazifa №7
**Savol:** So‘z qo‘shilmasi ishtirok etgan gap?
**Javob:** A) Dadam yo bugun keladi, yo ertaga kechqurun keladi.

### 8. Vazifa №8
**Savol:** Mazmun va grammatik bog'liqlik?
**Javob:** 1 va 2

### 9. Vazifa №9
**Savol:** Bog'lovchi vosita? "Donolik bilim emas, ... uni qo‘llashni bilishdir."
**Javob:** B) chunki

### 10. Vazifa №10
**Savol:** Sifat turkumi qo'llangan?
**Javob:** C) Har ikkala gapda ham sifat turkumiga mansub birlik ishtirok etgan.

*(Eslatma: Qolgan 5 ta savol AI yordamchisida batafsil tushuntiriladi)*
"""
}

FACTS_DATA = [
    "🍯 Asal 3000 yil tursa ham buzilmaydi.",
    "🐙 Sakkizoyoqlarning qoni ko'k rangda bo'ladi.",
    "🦒 Zirafalar kuniga faqat 30 daqiqa uxlashadi.",
    "🐜 Dunyodagi chumolilar og'irligi barcha odamlar og'irligiga teng.",
    "🐘 Fillar sakray olmaydigan yagona sutemizuvchidir."
]

# --- BACKGROUND REMINDER ---
async def reminder_loop():
    while True:
        now = datetime.now().strftime("%H:%M")
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT id, user_id, task_text FROM tasks WHERE remind_time = ? AND is_done = 0", (now,)) as cursor:
                reminders = await cursor.fetchall()
                for rid, uid, text in reminders:
                    try:
                        await bot.send_message(uid, f"⏰ *ESLATMA (SIGNAL)!*\n\nVazifa vaqti keldi:\n👉 *{text}*", parse_mode="Markdown")
                        # Faqat birmarta signal berish
                        await db.execute("UPDATE tasks SET remind_time = NULL WHERE id = ?", (rid,))
                    except:
                        pass
            await db.commit()
        await asyncio.sleep(60) # Har daqiqada tekshirish

# --- UI ---
def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🎨 Kreativ darslar"))
    builder.row(types.KeyboardButton(text="📚 Darsliklar (1-11)"), types.KeyboardButton(text="🧩 Bilim testi"))
    builder.row(types.KeyboardButton(text="📊 BSB (Nazorat)"), types.KeyboardButton(text="📅 Taqvim rejalar"))
    builder.row(types.KeyboardButton(text="🎥 Video darslar"), types.KeyboardButton(text="📝 Onlayn testlar"))
    builder.row(types.KeyboardButton(text="🤖 AI Yordamchi"), types.KeyboardButton(text="💡 Motivatsiya"))
    builder.row(types.KeyboardButton(text="🌍 G'aroyib Faktlar"), types.KeyboardButton(text="📝 Vazifalarim"))
    return builder.as_markup(resize_keyboard=True)






@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username)
    
    welcome_text = (
        "👋 *Salom, aziz o'quvchi!* \n\n"
        "✨ *'ZUKKO YORDAMCHI'* platformasiga xush kelibsiz! 🚀\n\n"
        "Mening vazifam — darslaringizni oson va qiziqarli qilish.\n"
        "📚 *Darsliklar*, 📊 *BSB yechimlari* va 🤖 *AI yordamchi* — barchasi bir joyda.\n\n"
        "⚠️ *Muhim:* Botdan foydalanish orqali siz o'z ma'lumotlaringiz (ID, ism) "
        "ta'limiy maqsadlarda qayta ishlanishiga rozilik berasiz.\n\n"
        "👇 *Pastdan kerakli bo'limni tanlang:*"
    )
    
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu())

@dp.message(F.text == "💡 Motivatsiya")
async def show_motivation(message: types.Message):
    quote = random.choice(MOTIVATION_DATA)
    await message.answer(quote, parse_mode="Markdown")

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    help_text = (
        "❓ *Yordam va Yo'riqnoma:*\n\n"
        "Bot nomi: *Zukko Yordamchi*\n\n"
        "1. 📚 *Darsliklar* — Barcha sinflar uchun PDF kitoblar.\n"
        "2. 📊 *BSB* — Nazorat ishlari va namunalar.\n"
        "3. 🤖 *AI Yordamchi* — Savollaringizga ilmiy javoblar.\n"
        "4. 🎨 *Kreativlik* — O'qituvchilar uchun metodlar.\n\n"
        "✅ _Tizim 24/7 rejimida ishlaydi._"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("about"))
async def about_cmd(message: types.Message):
    about_text = (
        "🏢 *LOYIHA HAQIDA:*\n\n"
        "✨ *'Zukko Yordamchi'* — maktab o'quvchilari uchun ta'limni osonlashtirish maqsadida yaratilgan zamonaviy platforma.\n\n"
        "🛡 *Xavfsizlik*: Ma'lumotlar faqat ta'limga yo'naltirilgan.\n"
        "📜 *Versiya*: 3.2 (Compliance update)\n\n"
        "📄 *Maxfiylik*: Bot [O'zR Shaxsga doir ma'lumotlar to'g'risida](https://lex.uz/docs/4396419)gi qonuniga muvofiq ishlaydi."
    )
    await message.answer(about_text, parse_mode="Markdown")




@dp.message(F.text == "📚 Darsliklar (1-11)")
async def show_grades(message: types.Message):
    builder = InlineKeyboardBuilder()
    for g in range(1, 12):
        builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"gr_{g}"))
    builder.adjust(3)
    await message.answer("📁 *Sinfingizni tanlang:*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("gr_"))
async def show_books(callback: types.CallbackQuery):
    grade_num = callback.data.split('_')[1]
    books = BOOKS_DATA.get(grade_num, [])
    builder = InlineKeyboardBuilder()
    for name, link in books:
        builder.row(types.InlineKeyboardButton(text=name, url=link))
    builder.row(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_grades"))
    await callback.message.edit_text(
        f"📚 *{grade_num}-sinf darsliklari:*\n"
        f"Quyidagi fanlardan birini tanlang 👇",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_grades")
async def back_grades(callback: types.CallbackQuery):
    await show_grades(callback.message)
    await callback.answer()

@dp.message(F.text == "🧩 Bilim testi")
async def play_quiz(message: types.Message):
    q = random.choice(GAMES_DATA)
    builder = InlineKeyboardBuilder()
    for o in q["o"]:
        builder.add(types.InlineKeyboardButton(text=o, callback_data=f"ans_{o}_{GAMES_DATA.index(q)}"))
    await message.answer(f"❓ *SAVOL:* {q['q']}", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("ans_"))
async def check_ans(callback: types.CallbackQuery):
    ans, idx = callback.data.split("_")[1], int(callback.data.split("_")[2])
    if ans == GAMES_DATA[idx]["a"]:
        await callback.message.edit_text(f"✅ *TO'G'RI!*", parse_mode="Markdown")
    else:
        await callback.message.edit_text(f"❌ *XATO!* To'g'ri javob: {GAMES_DATA[idx]['a']}", parse_mode="Markdown")
    await callback.answer()

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c1:
            total_users = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM tasks") as c2:
            total_tasks = (await c2.fetchone())[0]
            
    text = (
        "👨‍💻 *ADMIN PANELI*\n\n"
        f"👥 Foydalanuvchilar: `{total_users}` nafar\n"
        f"📝 Jami vazifalar: `{total_tasks}` ta"
    )
    await message.answer(text, parse_mode="Markdown")

# Reklama funksiyasi o'chirildi

@dp.message(F.text == "🌍 G'aroyib Faktlar")

async def show_fact(message: types.Message):
    fact = random.choice(FACTS_DATA)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🔄 Keyingi", callback_data="next_fact"))
    await message.answer(f"💡 *BILASIZMI?*\n\n{fact}", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.message(F.text == "🎥 Video darslar")
async def video_lessons(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📺 Maktab darslari (YouTube)", url="https://www.youtube.com/@uzeduuz/playlists"))
    builder.row(types.InlineKeyboardButton(text="🎓 Khan Academy (O'zbek)", url="https://uz.khanacademy.org/"))
    await message.answer("🎥 *Video darslar bo'limi:*\n\nEng sara video darslarni quyidagi kanallar orqali tomosha qilishingiz mumkin:", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.message(F.text == "📝 Onlayn testlar")
async def online_tests(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🎓 Bilimni Baholash Agentligi", url="https://uzbmb.uz/"))
    builder.row(types.InlineKeyboardButton(text="🏆 Olimpiada Portali", url="https://olimpiada.uzedu.uz/"))
    builder.row(types.InlineKeyboardButton(text="🏛 Maktab.uz (Dars va Testlar)", url="https://maktab.uz/"))
    
    await message.answer(
        "📝 *Onlayn testlar va Mashqlar:*\n\n"
        "O'z bilimingizni ishonchli va xavfsiz ta'lim portallarida sinab ko'ring. "
        "Eng sara manbalar tanlab olindi 👇",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )


@dp.message(F.text == "📊 BSB (Nazorat)")
async def bsb_section(message: types.Message):
    builder = InlineKeyboardBuilder()
    for g in range(5, 12):
        builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"bsb_{g}"))
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="📅 BSB Mezonlari (Rasmiy)", url="https://trm.uz/page/baholash-va-monitoring"))
    builder.row(types.InlineKeyboardButton(text="📂 Metodik qo'llanmalar", url="https://trm.uz/"))
    await message.answer(
        "📊 *BSB (Nazorat ishlari) bo'limi:*\n\n"
        "Sinfingizni tanlang va rasmiy metodik tavsiyalarni ko'rib chiqing 👇\n\n"
        "✨ *AD-FREE:* Tashqi saytlardagi reklamalardan charchadingizmi? "
        "Yaxshisi, *test rasmiga olib yuboring*, AI barchasini reklamasiz yechib beradi! 🤖",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )

@dp.message(F.text == "📅 Taqvim rejalar")
async def taqvim_section(message: types.Message):
    builder = InlineKeyboardBuilder()
    for g in range(1, 12):
        builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"taqvim_{g}"))
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="📂 Rasmiy Resurslar (Maktab.uz)", url="https://maktab.uz/"))
    builder.row(types.InlineKeyboardButton(text="📢 eMaktab Yordam Markazi", url="https://help.emaktab.uz/"))
    
    await message.answer(
        "📅 *Taqvim-mavzu rejalar (2025-2026):*\n\n"
        "Yangi o'quv yili uchun tasdiqlangan rejalar va dars taqsimoti 👇\n\n"
        "⚠️ *Ogohlantirish:* Tashqi havolalarda reklamalar bo'lishi mumkin. "
        "Biz faqat eng ishonchli davlat portallarini tavsiya etamiz.",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("bsb_"))
async def show_bsb_links(callback: types.CallbackQuery):
    grade = callback.data.split("_")[1]
    text = (
        f"📊 *{grade}-sinf BSB bo'limi*\n\n"
        "Tashqi saytlardagi reklamalardan xoli bo'lish uchun rasmiy manbalardan foydalaning 👇\n\n"
        "💡 *Maslahat:* Eng yaxshi yo'l — *test rasmini botga yuborish*. AI uni darhol reklamasiz yechib beradi!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📂 TRM.uz (Rasmiy mezonlar)", url="https://trm.uz/"))
    builder.row(types.InlineKeyboardButton(text="📖 eMaktab Yordam", url="https://help.emaktab.uz/"))
    builder.row(types.InlineKeyboardButton(text="🤖 AI orqali yechish (FOTO)", callback_data="ai_help"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_bsb"))
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("taqvim_"))
async def show_taqvim_links(callback: types.CallbackQuery):
    grade = callback.data.split("_")[1]
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🏛 Maktab.uz resurslari", url="https://maktab.uz/"))
    builder.row(types.InlineKeyboardButton(text="📅 Ish rejalar (Rasmiy)", url="https://trm.uz/"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_taqvim"))
    
    await callback.message.edit_text(
        f"📅 *{grade}-sinf Taqvim Rejalari*\n\n"
        "Tasdiqlangan ish rejalarini rasmiy portallardan yuklab olishingiz mumkin 👇",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_taqvim")
async def back_taqvim(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for g in range(1, 12):
        builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"taqvim_{g}"))
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="📂 Maktab.uz Portal", url="https://maktab.uz/"))
    await callback.message.edit_text(
        "📅 *Taqvim-mavzu rejalar bo'limi:*\n\nSinfingizni tanlang 👇",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_bsb")
async def back_bsb(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for g in range(5, 12):
        builder.add(types.InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"bsb_{g}"))
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="📂 Metodik tavsiyalar", url="https://trm.uz/"))
    await callback.message.edit_text(
        "📊 *BSB (Baho-Sifat-Bilim) bo'limi:*\n\nSinfingizni tanlang 👇",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# CHSB bo'limi olib tashlandi

@dp.callback_query(F.data.startswith("internal_"))
async def show_internal_answer(callback: types.CallbackQuery):
    key = callback.data.replace("internal_", "")
    content = INTERNAL_ANSWERS.get(key, "Ma'lumot topilmadi.")
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_chsb"))
    
    # Agar matn juda uzun bo'lsa, bo'lib yuborish kerak bo'lishi mumkin
    if len(content) > 4000:
        await callback.message.answer(content[:4000], parse_mode="Markdown")
        await callback.message.answer(content[4000:], parse_mode="Markdown", reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text(content, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

# Back CHSB bo'limi olib tashlandi


@dp.message(F.text.ilike("%kreativ%"))
@dp.message(F.text == "🎨 Kreativ darslar")
async def creative_games_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    for subject in KREATIV_GAMES.keys():
        builder.add(types.InlineKeyboardButton(text=subject, callback_data=f"kreativ_{subject}"))
    builder.adjust(2)
    await message.answer("🎨 *Qaysi fan uchun kreativ metod kerak?*", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("kreativ_"))
async def show_kreativ_game(callback: types.CallbackQuery):
    subject = callback.data.split("_")[1]
    games = KREATIV_GAMES.get(subject, {})
    
    text = f"🎨 *{subject}* bo'yicha kreativ o'yinlar va metodlar:\n\n"
    builder = InlineKeyboardBuilder()
    
    for name, info in games.items():
        if info.startswith("http"):
            builder.row(types.InlineKeyboardButton(text=f"🌐 {name}", url=info))
        else:
            text += f"🔹 *{name}*:\n_{info}_\n\n"
    
    builder.row(types.InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_kreativ"))
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "back_kreativ")
async def back_kreativ(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for subject in KREATIV_GAMES.keys():
        builder.add(types.InlineKeyboardButton(text=subject, callback_data=f"kreativ_{subject}"))
    builder.adjust(2)
    await callback.message.edit_text("🎨 *Qaysi fan uchun kreativ metod kerak?*", parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

@dp.message(F.text == "🤖 AI Yordamchi")
async def ai_assistant_cmd(message: types.Message):
    await start_ai_session(message.from_user.id, message)

async def start_ai_session(user_id: int, message: types.Message):
    ai_sessions.add(user_id)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="❌ AI rejimidan chiqish", callback_data="exit_ai"))
    msg = (
        "🤖 *AI Yordamchi faollashdi!* \n\n"
        "Menga istalgan savolingizni yozib yuboring. Masalan:\n"
        "• _Fotosintez jarayonini tushuntir_\n"
        "• _Pifagor teoremasi nima?_\n\n"
        "⚠️ *Eslatma:* AI javoblarida xatoliklar bo'lishi mumkin. "
        "Muhim ma'lumotlarni darslik bilan solishtiring.\n\n"
        "💡 _Chiqish uchun pastdagi tugmani bosing._"
    )
    await bot.send_message(user_id, msg, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "exit_ai")
async def exit_ai_mode(callback: types.CallbackQuery):
    ai_sessions.discard(callback.from_user.id)
    await callback.message.edit_text("✅ *AI rejimidan chiqildi.*", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "next_fact")
async def next_fact(callback: types.CallbackQuery):
    fact = random.choice(FACTS_DATA)
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🔄 Keyingi", callback_data="next_fact"))
    await callback.message.edit_text(f"💡 *BILASIZMI?*\n\n{fact}", parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

# Reyting olib tashlandi

def get_sand_glass(created_at, remind_time):
    if not remind_time or not created_at: return ""
    try:
        now = datetime.now()
        start = datetime.strptime(created_at, "%Y-%m-%d %H:%M")
        end = datetime.strptime(now.strftime("%Y-%m-%d ") + remind_time, "%Y-%m-%d %H:%M")
        
        total_sec = (end - start).total_seconds()
        passed_sec = (now - start).total_seconds()
        
        if total_sec <= 0: return "⌛ [■■■■■■] ⏳"
        percent = min(100, max(0, int((passed_sec / total_sec) * 100)))
        
        filled = percent // 15
        bar = "■" * filled + "□" * (6 - filled)
        return f"⌛ [{bar}] ⏳"
    except:
        return "⌛"

@dp.message(F.text == "📝 Vazifalarim")
async def show_tasks(message: types.Message):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT id, task_text, remind_time, created_at FROM tasks WHERE user_id = ? AND is_done = 0", (message.from_user.id,)) as cursor:
            tasks = await cursor.fetchall()
    
    if not tasks:
        await message.answer("📝 *Vazifalar yo'q.*\n\nQo'shish: `vazifa dars @ 19:00`", parse_mode="Markdown")
        return

    builder = InlineKeyboardBuilder()
    text = "📝 *SIZNING VAZIFALARINGIZ:* \n\n"
    for tid, task, r_time, c_time in tasks:
        progress = get_sand_glass(c_time, r_time)
        text += f"📌 *{task}* \n{progress} {r_time if r_time else ''}\n\n"
        builder.row(types.InlineKeyboardButton(text=f"✅ Bajarildi: {task[:15]}", callback_data=f"done_{tid}"))
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("done_"))
async def mark_task_done(callback: types.CallbackQuery):
    task_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE tasks SET is_done = 1 WHERE id = ?", (task_id,))
        await db.commit()
    await callback.answer("✅ Bajarildi!")
    await callback.message.delete()

@dp.message(F.text.startswith("vazifa "))
async def add_task_cmd(message: types.Message):
    text = message.text.replace("vazifa ", "").strip()
    remind_time = None
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if " @ " in text:
        parts = text.split(" @ ")
        text = parts[0].strip()
        remind_time = parts[1].strip()

    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT INTO tasks (user_id, task_text, remind_time, created_at) VALUES (?, ?, ?, ?)", (message.from_user.id, text, remind_time, created_at))
        await db.commit()
    
    msg = f"✅ Saqlandi: *{text}*"
    if remind_time: msg += f"\n⌛ Qum soati ishga tushdi: *{remind_time}*"
    await message.answer(msg, parse_mode="Markdown")

# Startup bo'limi olib tashlandi



# Bonus bo'limi olib tashlandi

# Xavfsiz ta'lim bo'limi olib tashlandi


# --- AI SAVOLLARGA JAVOB (barcha boshqa xabarlar uchun) ---
@dp.message(F.photo)
async def handle_photo_test(message: types.Message):
    thinking = await message.answer("🖼 _Rasm qabul qilindi. AI testni yechmoqda... Kuting_ ⏳", parse_mode="Markdown")
    try:
        # Eng yuqori sifatdagi rasmni olish
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded = await bot.download_file(file_info.file_path)
        image_buffer = downloaded.read()
        
        # Rasmni AI ga yuborish va javobni olish
        response = await solve_test_from_image(image_buffer)
        
        # Javobni qaytarish (agar markdown noto'g'ri bo'lsa, oddiy matn sifatida yuboramiz)
        try:
            await thinking.edit_text(f"✅ *TEST / SAVOL JAVOBI:*\n\n{response}", parse_mode="Markdown")
        except:
            await thinking.edit_text(f"✅ TEST / SAVOL JAVOBI:\n\n{response}")
    except Exception as e:
        await thinking.edit_text(f"❌ Xato yuz berdi: {str(e)[:150]}")

@dp.callback_query(F.data == "ai_help")
async def ai_help_shortcut(callback: types.CallbackQuery):
    await start_ai_session(callback.from_user.id, callback.message)
    await callback.answer()

@dp.message()
async def handle_free_text(message: types.Message):
    if message.from_user.id in ai_sessions:
        thinking = await message.answer("🤖 _AI o'ylanmoqda..._", parse_mode="Markdown")
        try:
            response = await ask_gemini(message.text)
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(text="❌ AI rejimidan chiqish", callback_data="exit_ai"))
            try:
                footer = "\n\n⚠️ _AI xato qilishi mumkin. Rasmiy manbalarni ham tekshiring._"
                await thinking.edit_text(f"🤖 *AI javobi:*\n\n{response}{footer}", parse_mode="Markdown", reply_markup=builder.as_markup())
            except:
                await thinking.edit_text(f"🤖 AI javobi:\n\n{response}", reply_markup=builder.as_markup())
        except Exception as e:
            await thinking.edit_text(f"❌ Xatolik: {str(e)[:200]}")
    else:
        if not message.text.startswith("/"):
            await message.answer("Iltimos, menyudan kerakli bo'limni tanlang 👇", reply_markup=main_menu())

async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="start", description="Botni qayta ishga tushirish"),
        types.BotCommand(command="help", description="Yordam va yo'riqnoma"),
        types.BotCommand(command="about", description="Loyiha haqida ma'lumot")
    ]
    await bot.set_my_commands(commands)

async def handle(request):
    """Render health check uchun oddiy sahifa"""
    return web.Response(text="Bot is running! 🚀")

async def main():
    await init_db()
    # Rasmiy buyruqlar menyusini o'rnatish
    await set_commands(bot)
    
    # Render'da bot o'chib qolmasligi uchun kichik Web Server
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    asyncio.create_task(site.start())
    logging.info(f"Web server started on port {port}")

    # Reminder tizimini fonda ishga tushirish
    asyncio.create_task(reminder_loop())
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
