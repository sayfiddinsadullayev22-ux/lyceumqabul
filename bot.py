import asyncio
import logging
import sqlite3
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [7618889413, 5541894729]
WEBINAR_LINK = "https://t.me/+VT0CQQ0n4ag4YzQy"
REQUIRED_REFERRALS = 3

# ================= INIT =================

bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    full_name TEXT,
    referrer INTEGER,
    referrals INTEGER DEFAULT 0
)
""")
conn.commit()

# ================= FUNCTIONS =================

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    return cursor.fetchone()

def get_referrals(user_id):
    cursor.execute("SELECT referrals FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def progress_bar(count):
    filled = "🟢" * min(count, REQUIRED_REFERRALS)
    empty = "⚪" * (REQUIRED_REFERRALS - min(count, REQUIRED_REFERRALS))
    return filled + empty

# ================= START =================

@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    args = message.text.split()

    referrer = None
    if len(args) > 1:
        try:
            referrer = int(args[1])
        except:
            pass

    exists = get_user(user_id)

    if not exists:
        if referrer == user_id:
            referrer = None

        cursor.execute(
            "INSERT INTO users (id, full_name, referrer, referrals) VALUES (?, ?, ?, 0)",
            (user_id, full_name, referrer)
        )
        conn.commit()

        if referrer and referrer not in ADMIN_IDS:
            cursor.execute(
                "UPDATE users SET referrals = referrals + 1 WHERE id=?",
                (referrer,)
            )
            conn.commit()

            new_count = get_referrals(referrer)

            await bot.send_message(
                referrer,
                f"🎉 Sizga yangi do'st qo‘shildi!\n\n"
                f"👤 Ismi: {full_name}\n"
                f"⭐ Sizning balingiz: {new_count}/{REQUIRED_REFERRALS}\n"
                f"{progress_bar(new_count)}"
            )

    await send_main_menu(message)

# ================= MENU =================

async def send_main_menu(message):
    user_id = message.from_user.id
    count = get_referrals(user_id)

    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={user_id}"

    text = (
        "Ramazon Challenge’ga qatnashish uchun quyidagi ketma-ketlikni bajaring\n\n"
        "1. “Do’stlarga ulashish” tugmasini bosib, 3ta do’stingizni taklif qiling\n\n"
        "2. “Webinar”ga qo’shilishni bosing, va biz sizga yopiq kanal linkini beramiz\n\n"
        f"⭐ Sizning balingiz: {count}/{REQUIRED_REFERRALS}\n"
        f"{progress_bar(count)}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👥 Do'st taklif qilish",
                url=f"https://t.me/share/url?url={referral_link}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎓 Webinar",
                callback_data="webinar"
            )
        ]
    ])

    await message.answer(text, reply_markup=keyboard)

# ================= WEBINAR =================

@dp.callback_query(F.data == "webinar")
async def webinar_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = get_referrals(user_id)

    if count >= REQUIRED_REFERRALS:
        await callback.message.answer(
            f"✅ Tabriklaymiz!\n\n"
            f"Yopiq kanal link:\n{WEBINAR_LINK}"
        )
    else:
        await callback.message.answer(
            f"❌ Siz hali 3 ta do‘st taklif qilmagansiz.\n\n"
            f"⭐ {count}/{REQUIRED_REFERRALS}\n"
            f"{progress_bar(count)}"
        )

    await callback.answer()

# ================= STATS =================

@dp.message(Command("stats"))
async def stats_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(referrals) FROM users")
    total_refs = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT full_name, referrals
        FROM users
        ORDER BY referrals DESC
        LIMIT 5
    """)
    top_users = cursor.fetchall()

    top_text = ""
    for i, user in enumerate(top_users, start=1):
        top_text += f"{i}. {user[0]} — {user[1]} ball\n"

    await message.answer(
        f"📊 Statistika\n\n"
        f"👥 Foydalanuvchilar: {total_users}\n"
        f"🔗 Jami referallar: {total_refs}\n\n"
        f"🏆 Top 5:\n{top_text if top_text else 'Ma’lumot yo‘q'}"
    )

# ================= RUN =================

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())