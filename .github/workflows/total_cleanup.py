import os
import re

path = r'c:\Users\user\Documents\Elyor\TAXI.bot\bot.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# The error is a multi-line string with single quotes created by previous re.sub
# We RE-WRTE the whole reg_finish block cleanly
new_reg_finish = r"""@dp.message(RegState.entering_phone, F.contact)
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
            await db.commit()
            
        if role == "driver":
            msg = "🎉 Muvaffaqiyatli ro'yxatdan o'tdingiz!\n🎁 Sizga haydovchi sifatida 30 kunlik bepul sinov muddati berildi!"
        else:
            msg = "🎉 Muvaffaqiyatli ro'yxatdan o'tdingiz!\n🚀 Botdan umrbod bepul foydalanishingiz mumkin. Safarni boshlash uchun quyidagi menyudan foydalaning!"
            
        await m.answer(msg, reply_markup=await mkb(uid))
        await state.clear()
    except Exception as e:
        logger.error(f"Error in reg_finish: {e}")
        await m.answer("❌ Ro'yxatdan o'tishda xatolik yuz berdi. Iltimos qayta /start bosing.")
"""

# Find the broken part and replace it
# The pattern will look for reg_finish until state.clear() or similar
pattern = r'@dp\.message\(RegState\.entering_phone, F\.contact\)\s+async def reg_finish\(m: types\.Message, state: FSMContext\):.*?await state\.clear\(\)'
content = re.sub(pattern, new_reg_finish, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Full reg_finish cleanup completed.")
