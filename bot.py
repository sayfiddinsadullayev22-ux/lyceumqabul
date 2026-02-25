import asyncio
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command

# ================= CONFIG =================
TOKEN = "8246098957:AAGtD7OGaD4ThJVGlJM6SSlLkGZ37JV5SY0"
ADMIN_IDS = [7618889413, 5541894729]
CHANNELS = ["@Mirzokhid_blog", "@lyceumverse"]  # Majburiy kanallar
WEBINAR_LINK = "https://t.me/+VT0CQQ0n4ag4YzQy"
REQUIRED_REFERRALS = 3
MAX_POINTS_BAR = 5

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB_PATH = "database.db"

# ================= DB INIT =================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            referrer INTEGER,
            referrals INTEGER DEFAULT 0,
            last_menu_message_id INTEGER
        )
        """)
        await db.commit()

# ================= HELPERS =================
async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE id=?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def get_referrals(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT referrals FROM users WHERE id=?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

def progress_bar(count):
    filled = "🟢" * min(count, MAX_POINTS_BAR)
    empty = "⚪" * (MAX_POINTS_BAR - min(count, MAX_POINTS_BAR))
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
        new_count = await get_referrals(referrer_id)
        return new_count

# ================= MENU =================
async def send_main_menu(message):
    user_id = message.from_user.id
    count = await get_referrals(user_id)
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={user_id}"

    subscribed = await is_subscribed(user_id)

    if not subscribed:
        text = "✅ Iltimos, avval quyidagi kanallarga obuna bo‘ling:"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=ch, url=f"https://t.me/{ch.replace('@','')}")] for ch in CHANNELS]
        )
        sent_message = await message.answer(text, reply_markup=keyboard)
    else:
        text = (
            "Ramazon Challenge’ga qatnashish uchun quyidagi ketma-ketlikni bajaring\n\n"
            "1. Do‘stlarga referral yuboring\n"
            "2. 3 ta referral to‘plaganingizdan keyin Webinar orqali yopiq kanal linkini oling\n\n"
            f"⭐ Sizning balingiz: {count}/{REQUIRED_REFERRALS}\n"
            f"{progress_bar(count)}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Do'st taklif qilish", url=referral_link)],
            [InlineKeyboardButton(text="🎓 Webinar", callback_data="webinar")]
        ])
        sent_message = await message.answer(text, reply_markup=keyboard)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_menu_message_id=? WHERE id=?",
            (sent_message.message_id, user_id)
        )
        await db.commit()

# ================= START HANDLER =================
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    args = message.text.split()
    referrer = None
    if len(args) > 1:
        try:
            referrer = int(args[1])
            if referrer == user_id:
                referrer = None
        except:
            pass

    user = await get_user(user_id)
    if not user:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO users (id, full_name, referrer, referrals) VALUES (?, ?, ?, 0)",
                (user_id, full_name, referrer)
            )
            await db.commit()
        if referrer and referrer not in ADMIN_IDS:
            new_count = await increment_referral(referrer)
            await bot.send_message(referrer, f"🎉 Sizga yangi do‘st qo‘shildi!\n👤 Ismi: {full_name}\n⭐ Ballingiz: {new_count}/{REQUIRED_REFERRALS}")
    await send_main_menu(message)

# ================= CALLBACKS =================
@dp.callback_query(F.data=="webinar")
async def webinar_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = await get_referrals(user_id)
    subscribed = await is_subscribed(user_id)

    if not subscribed:
        await callback.message.answer("❌ Siz kanalga obuna bo‘lmagansiz. Iltimos, obuna bo‘ling.")
        await callback.answer()
        return

    if count >= REQUIRED_REFERRALS:
        await callback.message.answer(f"✅ Tabriklaymiz! Yopiq kanal link:\n{WEBINAR_LINK}")
    else:
        await callback.message.answer(f"❌ Siz hali {REQUIRED_REFERRALS} ta referral to‘plamagansiz.\n⭐ {count}/{REQUIRED_REFERRALS}\n{progress_bar(count)}")
    await callback.answer()

# ================= STATS =================
@dp.message(Command("stats"))
async def stats_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, full_name, referrer, referrals FROM users") as cursor:
            users = await cursor.fetchall()
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