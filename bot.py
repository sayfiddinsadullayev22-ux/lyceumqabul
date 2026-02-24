import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ================= CONFIG =================
TOKEN = "8246098957:AAGtD7OGaD4ThJVGlJM6SSlLkGZ37JV5SY0"
ADMIN_IDS = [7618889413, 5541894729]
CHANNELS = ["@Mirzokhid_blog", "@lyceumverse"]
WEBINAR_LINK = "https://t.me/+VT0CQQ0n4ag4YzQy"
REQUIRED_REFERRALS = 2
MAX_POINTS_BAR = 5
BOT_USERNAME = "8246098957:AAGtD7OGaD4ThJVGlJM6SSlLkGZ37JV5SY0"  # <--- Bot username
# ==========================================

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)
dp = Dispatcher()

# ================= DATABASE =================
db = sqlite3.connect("database.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    points INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    joined_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS invites(
    user_id INTEGER PRIMARY KEY,
    invited_by INTEGER
)
""")

db.commit()

# ================= DB FUNCTIONS =================
def add_user(user_id, username):
    cursor.execute("""
    INSERT OR IGNORE INTO users(user_id, username, joined_at)
    VALUES(?,?,?)
    """, (user_id, username or "Do‘st", datetime.now().strftime("%Y-%m-%d %H:%M")))
    db.commit()

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def add_points(user_id, amount=1):
    cursor.execute("UPDATE users SET points=points+? WHERE user_id=?", (amount, user_id))
    db.commit()

def add_referral(user_id):
    cursor.execute("UPDATE users SET referrals=referrals+1 WHERE user_id=?", (user_id,))
    db.commit()

def user_bar(points, max_points=MAX_POINTS_BAR):
    full_block = "🟩"
    empty_block = "⬜️"
    points = min(points, max_points)
    return full_block*points + empty_block*(max_points-points)

# ================= START =================
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Do‘st"

    add_user(user_id, username)

    # Referral ID tekshirish
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id:
            cursor.execute("SELECT * FROM invites WHERE user_id=?", (user_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO invites(user_id, invited_by) VALUES(?,?)", (user_id, ref_id))
                add_points(ref_id, 1)
                add_referral(ref_id)
                db.commit()

    user = get_user(user_id)
    ref_count = user[3]  # referrals

    # Foydalanuvchining referal linki
    referal_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

    # Inline keyboard
    kb = InlineKeyboardBuilder()
    # Webinar tugmasi
    if ref_count >= REQUIRED_REFERRALS:
        kb.button(text="🟩🎥 Webinarga kirish", callback_data="webinar")
        webinar_msg = "Siz barcha shartlarni bajardingiz. Endi Webinar tugmasini bosib, qatnashishingiz mumkin."
    else:
        kb.button(text="🟩🎥 Webinar (referal yetarli emas)", callback_data="webinar_disabled")
        needed = REQUIRED_REFERRALS - ref_count
        webinar_msg = f"Webinarda qatnashish uchun kamida {REQUIRED_REFERRALS} referal kerak.\nHozir sizda {ref_count} referal bor. Yana {needed} ta do‘stingizni taklif qiling."

    # Referal tugmasi
    kb.button(text="🟩 Do‘stlarni taklif qil", url=referal_link)
    kb.adjust(1)

    msg_text = (
        f"👋 Salom, {username}!\n\n"
        f"{webinar_msg}\n\n"
        f"Sizning referal linkingiz: {referal_link}"
    )

    await message.answer(msg_text, reply_markup=kb.as_markup())

# ================= CALLBACKS =================
@dp.callback_query(F.data == "webinar")
async def webinar(call: CallbackQuery):
    user = get_user(call.from_user.id)
    if user[3] >= REQUIRED_REFERRALS:
        await call.message.edit_text(
            f"🎥 Webinar havolasi:\n{WEBINAR_LINK}\n✅ Sizda {user[3]} referal mavjud."
        )
    else:
        await call.answer("⚠️ Sizning referal soningiz yetarli emas.", show_alert=True)

@dp.callback_query(F.data == "webinar_disabled")
async def webinar_disabled(call: CallbackQuery):
    user = get_user(call.from_user.id)
    needed = max(0, REQUIRED_REFERRALS - user[3])
    await call.answer(f"⚠️ Hozir kamida {needed} ta qo‘shimcha referal kerak.", show_alert=True)

# ================= STATS =================
@dp.message(Command("stats"))
async def stats(message: Message):
    cursor.execute("SELECT username, points, referrals FROM users ORDER BY points DESC")
    users = cursor.fetchall()

    if not users:
        await message.answer("❌ Hozircha foydalanuvchilar yo‘q.")
        return

    text = "📊 Foydalanuvchilar jadvali\n\n"
    for user in users:
        bar = user_bar(user[1])
        text += f"{user[0] or 'Do‘st'} {bar} ⭐ ({user[1]} ball, {user[2]} referal)\n"

    await message.answer(text)

# ================= ADMIN PANEL =================
@dp.message(Command("panel"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(referrals) FROM users")
    total_refs = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(points) FROM users")
    total_points = cursor.fetchone()[0] or 0

    text = (
        "📊 ADMIN PANEL\n\n"
        f"👥 Jami user: {total}\n"
        f"🎁 Jami referal: {total_refs}\n"
        f"⭐ Jami ball: {total_points}"
    )

    await message.answer(text)

# ================= RUN =================
async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())