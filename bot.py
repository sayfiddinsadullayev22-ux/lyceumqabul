import asyncio
import logging
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ================= CONFIG =================
TOKEN = "8246098957:AAGtD7OGaD4ThJVGlJM6SSlLkGZ37JV5SY0"  # xavfsiz token qo'ying
ADMIN_IDS = [7618889413, 5541894729]
CHANNELS = ["@Mirzokhid_blog", "@lyceumverse"]  # Kanallar majburiy obuna
WEBINAR_LINK = "https://t.me/+VT0CQQ0n4ag4YzQy"
REQUIRED_REFERRALS = 2
MAX_POINTS_BAR = 5
BOT_USERNAME = "lyceumqabulbot"  # Telegram bot username
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

# ================= HELPER: CHECK SUBS =================
async def is_subscribed(user_id: int):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logging.warning(f"Channel check failed: {e}")
            return False
    return True

# ================= START =================
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Do‘st"
    add_user(user_id, username)

    # Referral tekshirish
    args = message.text.split()
    if len(args) > 1:
        try:
            ref_id = int(args[1])
            if ref_id != user_id:
                cursor.execute("SELECT * FROM invites WHERE user_id=?", (user_id,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO invites(user_id, invited_by) VALUES(?,?)", (user_id, ref_id))
                    add_points(ref_id, 1)
                    add_referral(ref_id)
                    db.commit()
        except:
            pass  # referral noto‘g‘ri kiritilgan bo‘lsa, e’tiborsiz qoldiramiz

    user = get_user(user_id)
    ref_count = user[3]
    subscribed = await is_subscribed(user_id)

    kb = InlineKeyboardBuilder()

    if not subscribed:
        for channel in CHANNELS:
            kb.button(text=f"🔔 Obuna bo‘ling {channel}", url=f"https://t.me/{channel.strip('@')}")
        kb.button(text="✅ Obunani tekshir", callback_data="check_sub")
        kb.adjust(1)
        msg_text = (
            f"👋 Salom, {username}!\n\n"
            "Webinar va referal ishlashi uchun barcha kanallarga obuna bo‘lishingiz kerak.\n"
            "Quyidagi tugmalar orqali kanallarga obuna bo‘ling, so‘ng ‘Obunani tekshir’ tugmasini bosing."
        )
    else:
        kb.button(text="🟩🎥 Webinarga kirish", callback_data="webinar")
        kb.button(text="🟩 Do‘stlarga ulashish", callback_data=f"get_ref_{user_id}")
        kb.adjust(1)
        msg_text = (
            f"👋 Salom, {username}!\n\n"
            f"Siz barcha kanallarga obuna bo‘lgansiz. Endi Webinar va referal tugmalari ishlaydi."
        )

    await message.answer(msg_text, reply_markup=kb.as_markup())

# ================= CALLBACKS =================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(call: CallbackQuery):
    subscribed = await is_subscribed(call.from_user.id)
    if subscribed:
        kb = InlineKeyboardBuilder()
        kb.button(text="🟩🎥 Webinarga kirish", callback_data="webinar")
        kb.button(text="🟩 Do‘stlarga ulashish", callback_data=f"get_ref_{call.from_user.id}")
        kb.adjust(1)
        await call.message.edit_text(
            "✅ Obuna tasdiqlandi! Endi Webinar va referal tugmalari ishlaydi.",
            reply_markup=kb.as_markup()
        )
    else:
        await call.answer("⚠️ Hali barcha kanallarga obuna bo‘lmadingiz.", show_alert=True)

@dp.callback_query(F.data == "webinar")
async def webinar(call: CallbackQuery):
    user = get_user(call.from_user.id)
    subscribed = await is_subscribed(user[0])
    if user[3] >= REQUIRED_REFERRALS and subscribed:
        await call.message.edit_text(
            f"🎥 Webinar havolasi:\n{WEBINAR_LINK}\n\n"
            f"✅ Sizda {user[2]} ball va {user[3]} referal mavjud."
        )
    else:
        needed_ref = max(0, REQUIRED_REFERRALS - user[3])
        msg = "⚠️ Shartlar yetarli emas.\n"
        if not subscribed:
            msg += "Iltimos, barcha kanallarga obuna bo‘ling.\n"
        if needed_ref > 0:
            msg += f"{needed_ref} ta referal yetishmayapti."
        await call.answer(msg, show_alert=True)

@dp.callback_query(F.data.startswith("get_ref_"))
async def get_referral(call: CallbackQuery):
    ref_user_id = call.from_user.id
    referral_link = f"https://t.me/{BOT_USERNAME}?start={ref_user_id}"
    text = (
        f"🎁 Referal tizimi:\n\n"
        f"📌 Har bir odam sizning referalingiz orqali kirsa — 1 ball olasiz.\n\n"
        f"🔗 Sizning referal linkingiz:\n{referral_link}\n\n"
        f"📤 Do‘stlaringizga ulashing!"
    )
    await call.message.answer(text)
    await call.answer("Referal link tayyor!", show_alert=True)

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