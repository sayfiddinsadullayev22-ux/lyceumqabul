import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command

# ================= CONFIG =================
TOKEN = "8246098957:AAGtD7OGaD4ThJVGlJM6SSlLkGZ37JV5SY0"
ADMIN_IDS = [7618889413, 5541894729]
CHANNELS = ["@Mirzokhid_blog", "@lyceumverse"]
WEBINAR_LINK = "https://t.me/+VT0CQQ0n4ag4YzQy"
REQUIRED_REFERRALS = 3
MAX_POINTS_BAR = 3  # progress bar ⚪️⚪️⚪️

bot = Bot(token=TOKEN)
dp = Dispatcher()
DB_PATH = "database.db"

# ================= INIT DB =================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            referrer INTEGER,
            referrals INTEGER DEFAULT 0,
            joined INTEGER DEFAULT 0
        )
        """)
        await db.commit()

# ================= HELPERS =================
async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE id=?", (user_id,)) as cur:
            return await cur.fetchone()

async def get_referrals(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT referrals FROM users WHERE id=?", (user_id,)) as cur:
            r = await cur.fetchone()
            return r[0] if r else 0

def progress_bar(count):
    filled = "🟢" * min(count, MAX_POINTS_BAR)
    empty = "⚪️" * (MAX_POINTS_BAR - min(count, MAX_POINTS_BAR))
    return filled + empty

async def is_subscribed(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status == "left":
                return False
        except:
            return False
    return True

async def increment_referral(referrer_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET referrals = referrals + 1 WHERE id=?", (referrer_id,))
        await db.commit()
        return await get_referrals(referrer_id)

# ================= START =================
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    args = message.text.replace("/start","").strip()
    referrer = None

    if args.startswith("ref_"):
        try:
            referrer = int(args.split("_")[1])
            if referrer == user_id:
                referrer = None
        except:
            referrer = None

    user = await get_user(user_id)
    if not user:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO users (id, full_name, referrer, referrals, joined) VALUES (?, ?, ?, 0, 1)",
                (user_id, full_name, referrer)
            )
            await db.commit()
        if referrer and referrer not in ADMIN_IDS:
            new_count = await increment_referral(referrer)
            await bot.send_message(referrer, f"🎉 Yangi do‘st qo‘shildi!\n👤 Ismi: {full_name}\n⭐ Ballingiz: {new_count}/{REQUIRED_REFERRALS}")
    await send_main_menu(message)

# ================= MENU =================
async def send_main_menu(message):
    user_id = message.from_user.id
    count = await get_referrals(user_id)
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    subscribed = await is_subscribed(user_id)

    if not subscribed:
        text = "✅ Iltimos, avval quyidagi kanallarga obuna bo‘ling:"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"📌 {ch}", url=f"https://t.me/{ch.replace('@','')}")] for ch in CHANNELS
            ] + [[InlineKeyboardButton(text="✅ Obunani tasdiqlash", callback_data="check_subs")]]
        )
        await message.answer(text, reply_markup=keyboard)
    else:
        text = (
            f"🎉 Ramazon Challenge’ga xush kelibsiz!\n\n"
            f"📌 Qoidalar:\n"
            f"1️⃣ Do‘stlarga referral yuboring.\n"
            f"2️⃣ 3 ta referral to‘plaganingizdan keyin Webinar orqali yopiq kanal linkini oling.\n\n"
            f"⭐️ Sizning balingiz: {count}/{REQUIRED_REFERRALS}\n"
            f"{progress_bar(count)}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Do‘st taklif qilish", callback_data="referral")],
            [InlineKeyboardButton(text="🎓 Webinar", callback_data="webinar")]
        ])
        await message.answer(text, reply_markup=keyboard)

# ================= REFERRAL =================
async def send_referral_info(message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    text = (
        "🎁 Referal tizimi:\n\n"
        "📌 Har bir odam sizning referalingiz orqali kirsa — 1 ball olasiz.\n\n"
        f"🔗 Sizning referal linkingiz:\n{referral_link}\n\n"
        "📤 Do‘stlaringizga ulashing!\n\n"
        f"Telegram ({referral_link})\nLyceumQabul\nLyceumverse tomonidan ishlab chiqilgan"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Nusxa olish", callback_data="copy_referral")],
        [InlineKeyboardButton(text="📩 Telegram orqali ulashish", url=f"https://t.me/share/url?url={referral_link}&text=Botga qo‘shiling")]
    ])
    await message.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data=="referral")
async def referral_handler(callback: CallbackQuery):
    await send_referral_info(callback.message)
    await callback.answer()

# ================= COPY REFERRAL =================
@dp.callback_query(F.data=="copy_referral")
async def copy_referral_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    text = (
        f"🔗 Sizning referal linkingiz:\n{referral_link}\n"
        "📤 Do‘stlaringizga ulashing!"
    )
    await callback.message.answer(text)
    await callback.answer("✅ Link yuborildi", show_alert=True)

# ================= CHECK SUBS =================
@dp.callback_query(F.data=="check_subs")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    if await is_subscribed(user_id):
        await callback.message.answer("✅ Kanalga obuna bo‘ldingiz!")
        await send_main_menu(callback.message)
    else:
        await callback.message.answer("❌ Siz hali barcha kanallarga obuna bo‘lmagansiz.")
    await callback.answer()

# ================= WEBINAR =================
@dp.callback_query(F.data=="webinar")
async def webinar_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = await get_referrals(user_id)
    if not await is_subscribed(user_id):
        await callback.message.answer("❌ Kanalga obuna bo‘lmadingiz.")
        await callback.answer()
        return
    if count >= REQUIRED_REFERRALS:
        await callback.message.answer(f"✅ Tabriklaymiz! Yopiq kanal link:\n{WEBINAR_LINK}")
    else:
        await callback.message.answer(f"❌ Siz hali {REQUIRED_REFERRALS} referral to‘plamagansiz.\n⭐ {count}/{REQUIRED_REFERRALS}\n{progress_bar(count)}")
    await callback.answer()

# ================= STATS =================
@dp.message(Command("stats"))
async def stats_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, full_name, referrer, referrals FROM users") as cur:
            users = await cur.fetchall()
    text = "📊 Hamma foydalanuvchilar:\n"
    for u in users:
        text += f"ID: {u[0]}, Ism: {u[1]}, Referrer: {u[2]}, Referrals: {u[3]}\n"
    await message.answer(text)

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())