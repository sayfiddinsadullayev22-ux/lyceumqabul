import asyncio
import aiosqlite
import random
import string
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command

# ================= CONFIG =================
TOKEN = "8246098957:AAGtD7OGaD4ThJVGlJM6SSlLkGZ37JV5SY0"
ADMIN_IDS = [7618889413, 5541894729]
CHANNELS = ["Mirzokhid_blog", "lyceumverse"]
WEBINAR_LINK = "https://t.me/+VT0CQQ0n4ag4YzQy"
REQUIRED_REFERRALS = 3
DB_PATH = r"C:\lyceumqabul\database.db"

bot = Bot(token=TOKEN)
dp = Dispatcher()
db = None  # Global DB connection

# ================= DB INIT =================
async def init_db():
    global db
    db = await aiosqlite.connect(DB_PATH)
    try:
        await db.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER;")
        await db.commit()
        print("✅ 'referrer_id' ustuni qo‘shildi.")
    except aiosqlite.OperationalError:
        print("✅ 'referrer_id' ustuni mavjud.")
    print("✅ DB ulanishi muvaffaqiyatli.")

# ================= HELPERS =================
def generate_ref_code():
    return ''.join(random.choices(string.digits, k=8))

async def get_user(user_id):
    async with db.execute("SELECT * FROM users WHERE id=?", (user_id,)) as cur:
        return await cur.fetchone()

async def get_user_by_refcode(ref_code):
    async with db.execute("SELECT * FROM users WHERE ref_code=?", (ref_code,)) as cur:
        return await cur.fetchone()

async def get_referrals(user_id):
    async with db.execute("SELECT referrals FROM users WHERE id=?", (user_id,)) as cur:
        r = await cur.fetchone()
        return r[0] if r else 0

def progress_bar(count):
    filled = "🟢" * min(count, REQUIRED_REFERRALS)
    empty = "⚪️" * (REQUIRED_REFERRALS - min(count, REQUIRED_REFERRALS))
    return filled + empty

async def increment_referral(referrer_id):
    user = await get_user(referrer_id)
    if not user:
        return 0
    await db.execute("UPDATE users SET referrals = referrals + 1 WHERE id=?", (referrer_id,))
    await db.commit()
    return await get_referrals(referrer_id)

async def is_subscribed(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{ch}", user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# ================= START =================
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    args = message.text.replace("/start","").strip()
    referrer = None

    if args.startswith("ref_"):
        parts = args.split("_", 1)
        if len(parts) == 2:
            ref_code = parts[1]
            ref_user = await get_user_by_refcode(ref_code)
            if ref_user:
                referrer = ref_user[0]
        if referrer == user_id:
            referrer = None

    user = await get_user(user_id)
    if not user:
        ref_code = generate_ref_code()
        await db.execute(
            "INSERT INTO users (id, full_name, referrer_id, referrals, ref_code) VALUES (?, ?, ?, ?, ?)",
            (user_id, full_name, referrer, 0, ref_code)
        )
        await db.commit()
        if referrer and referrer not in ADMIN_IDS:
            new_count = await increment_referral(referrer)
            try:
                await bot.send_message(referrer,
                    f"🎉 Yangi do‘st qo‘shildi!\n"
                    f"👤 Ismi: {full_name}\n"
                    f"⭐ Ballingiz: {new_count}/{REQUIRED_REFERRALS}\n"
                    f"{progress_bar(new_count)}"
                )
            except:
                pass
    await send_main_menu(message)

# ================= MENU =================
async def send_main_menu(message_or_callback):
    user_id = message_or_callback.from_user.id
    user = await get_user(user_id)
    if not user:
        return
    count = await get_referrals(user_id)
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user[4]}"
    subscribed = await is_subscribed(user_id)

    if not subscribed:
        text = "✅ Iltimos, quyidagi kanallarga obuna bo‘ling:"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"📌 @{ch}", url=f"https://t.me/{ch}")] for ch in CHANNELS
            ] + [[InlineKeyboardButton(text="✅ Obunani tasdiqlash", callback_data="check_subs")]]
        )
        if hasattr(message_or_callback, "message"):
            await message_or_callback.message.answer(text, reply_markup=keyboard)
            await message_or_callback.answer()
        else:
            await message_or_callback.answer(text, reply_markup=keyboard)
    else:
        text = (
            f"🎉 Ramazon Challenge’ga xush kelibsiz!\n\n"
            f"📌 Qoidalar:\n1️⃣ Do‘stlarga referral yuboring.\n"
            f"2️⃣ {REQUIRED_REFERRALS} ta referral to‘plangach Webinar orqali yopiq kanal linkini oling.\n\n"
            f"⭐ Ballingiz: {count}/{REQUIRED_REFERRALS}\n{progress_bar(count)}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Do‘st taklif qilish", callback_data="referral")],
            [InlineKeyboardButton(text="🎓 Webinar", callback_data="webinar")]
        ])
        if hasattr(message_or_callback, "message"):
            await message_or_callback.message.answer(text, reply_markup=keyboard)
            await message_or_callback.answer()
        else:
            await message_or_callback.answer(text, reply_markup=keyboard)

# ================= REFERRAL =================
async def send_referral_info(message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        ref_code = generate_ref_code()
        await db.execute(
            "INSERT INTO users (id, full_name, referrer_id, referrals, ref_code) VALUES (?, ?, ?, ?, ?)",
            (user_id, message.from_user.full_name, None, 0, ref_code)
        )
        await db.commit()
        user = await get_user(user_id)

    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user[4]}"
    count = await get_referrals(user_id)

    text = (
        f"🎁 Referral tizimi:\n"
        f"🔗 Sizning referal linkingiz:\n{referral_link}\n"
        f"⭐ Ballingiz: {count}/{REQUIRED_REFERRALS}\n{progress_bar(count)}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 Telegram orqali ulashish", url=f"https://t.me/share/url?url={referral_link}&text=Botga qo‘shiling")]
    ])
    await message.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data=="referral")
async def referral_handler(callback: CallbackQuery):
    await send_referral_info(callback.message)
    await callback.answer()

# ================= CHECK SUBS =================
@dp.callback_query(F.data=="check_subs")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    if await is_subscribed(user_id):
        await callback.message.answer("✅ Kanalga obuna bo‘ldingiz!")
        await send_main_menu(callback)
    else:
        await callback.message.answer("❌ Siz hali barcha kanallarga obuna bo‘lmagansiz.")
    await callback.answer()

# ================= WEBINAR =================
@dp.callback_query(F.data=="webinar")
async def webinar_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = await get_referrals(user_id)
    if not await is_subscribed(user_id):
        await callback.message.answer("❌ Kanalga obuna bo‘lmagansiz.")
        await callback.answer()
        return
    if count >= REQUIRED_REFERRALS:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Webinarga ulanish", url=WEBINAR_LINK)]
        ])
        await callback.message.answer("✅ Tabriklaymiz! Quyidagi tugma orqali webinarga ulaning:", reply_markup=keyboard)
    else:
        await callback.message.answer(f"❌ Siz hali {REQUIRED_REFERRALS} referral to‘plamagansiz.\n⭐ {count}/{REQUIRED_REFERRALS}\n{progress_bar(count)}")
    await callback.answer()

# ================= ADMIN =================
admin_broadcasts = {}

@dp.message(Command("xabar"))
async def broadcast_start(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    admin_broadcasts[message.from_user.id] = True
    await message.answer("📢 Admin: yubormoqchi bo‘lgan xabaringizni kiriting:")

@dp.message()
async def broadcast_handler(message: Message):
    if message.from_user.id in admin_broadcasts:
        async with db.execute("SELECT id FROM users") as cur:
            users = await cur.fetchall()
        for u in users:
            try:
                await bot.send_message(u[0], message.text)
            except:
                continue
        await message.answer("✅ Xabar barcha foydalanuvchilarga yuborildi.")
        admin_broadcasts.pop(message.from_user.id)

@dp.message(Command("stats"))
async def stats_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    async with db.execute("SELECT id, full_name, referrer_id, referrals, ref_code FROM users") as cur:
        users = await cur.fetchall()
    text = "📊 Hamma foydalanuvchilar:\n"
    for u in users:
        text += f"ID: {u[0]}, Ism: {u[1]}, Referrer: {u[2]}, Referrals: {u[3]}, Ref_code: {u[4]}\n"
    await message.answer(text)

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())