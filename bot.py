import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openpyxl import Workbook

# ================= CONFIG =================
TOKEN = "8246098957:AAGtD7OGaD4ThJVGlJM6SSlLkGZ37JV5SY0"
ADMIN_IDS = [7618889413 , 5541894729]  # Admin ID yoz
CHANNELS = ["@Mirzokhid_blog", "@lyceumverse"]  # Kanallar
WEBINAR_LINK = "https://t.me/yourlink"
REQUIRED_POINTS = 2
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
# ============================================

# ================= DB FUNCTIONS =================
def add_user(user_id, username):
    cursor.execute("""
    INSERT OR IGNORE INTO users(user_id, username, joined_at)
    VALUES(?,?,?)
    """, (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M")))
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

def total_users():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]
# =================================================

# ================= KEYBOARDS =================
def subscribe_kb():
    kb = InlineKeyboardBuilder()
    for ch in CHANNELS:
        kb.button(text=f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}")
    kb.button(text="✅ Obunani tasdiqlash", callback_data="check_sub")
    kb.adjust(1)
    return kb.as_markup()

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Shaxsiy kabinet", callback_data="profile")
    kb.button(text="🎁 Do‘st taklif qilish", callback_data="ref")
    kb.button(text="🏆 Reyting", callback_data="top")
    kb.button(text="🎥 Webinar", callback_data="webinar")
    kb.adjust(2,2)
    return kb.as_markup()

def back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Asosiy menyu", callback_data="back")
    return kb.as_markup()
# =================================================

# ================= FORCE SUB =================
async def check_subscription(user_id):
    try:
        for ch in CHANNELS:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member","administrator","creator"]:
                return False
        return True
    except:
        return False
# =================================================

# ================= START =================
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    add_user(user_id, username)

    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id:
            cursor.execute("SELECT * FROM invites WHERE user_id=?", (user_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO invites(user_id, invited_by) VALUES(?,?)",
                               (user_id, ref_id))
                add_points(ref_id, 1)
                add_referral(ref_id)
                db.commit()

    if not await check_subscription(user_id):
        await message.answer(
            "Assalomu alaykum 😊\n\n"
            "Botdan foydalanish uchun quyidagi rasmiy kanallarga obuna bo‘ling:",
            reply_markup=subscribe_kb()
        )
        return

    await message.answer(
        "Xush kelibsiz! 🎉\n\n"
        "Shaxsiy kabinetingiz orqali faolligingizni kuzatishingiz mumkin.",
        reply_markup=main_menu()
    )

    for admin in ADMIN_IDS:
        await bot.send_message(
            admin,
            f"🆕 Yangi user\nID: {user_id}\nJami: {total_users()}"
        )
# =================================================

# ================= CALLBACKS =================
@dp.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.message.edit_text(
            "Obuna tasdiqlandi ✅",
            reply_markup=main_menu()
        )
    else:
        await call.answer("Hali barcha kanallarga obuna bo‘lmagansiz.", show_alert=True)

@dp.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    user = get_user(call.from_user.id)
    text = (
        "👤 Shaxsiy kabinet\n\n"
        f"🆔 ID: {user[0]}\n"
        f"⭐ Ball: {user[2]}\n"
        f"👥 Referal: {user[3]}"
    )
    await call.message.edit_text(text, reply_markup=back_kb())

@dp.callback_query(F.data == "ref")
async def referral(call: CallbackQuery):
    link = f"https://t.me/{(await bot.me()).username}?start={call.from_user.id}"
    await call.message.edit_text(
        "🎁 Do‘stlarni taklif qiling!\n\n"
        f"Sizning havolangiz:\n{link}",
        reply_markup=back_kb()
    )

@dp.callback_query(F.data == "top")
async def leaderboard(call: CallbackQuery):
    cursor.execute("SELECT user_id, referrals FROM users ORDER BY referrals DESC LIMIT 10")
    top = cursor.fetchall()

    text = "🏆 TOP 10\n\n"
    for i, user in enumerate(top, 1):
        text += f"{i}. {user[0]} — {user[1]} ta\n"

    await call.message.edit_text(text, reply_markup=back_kb())

@dp.callback_query(F.data == "webinar")
async def webinar(call: CallbackQuery):
    user = get_user(call.from_user.id)
    if user[2] >= REQUIRED_POINTS:
        await call.message.edit_text(
            f"🎥 Webinar havolasi:\n{WEBINAR_LINK}",
            reply_markup=back_kb()
        )
    else:
        await call.answer(
            f"Webinar uchun kamida {REQUIRED_POINTS} ball kerak.",
            show_alert=True
        )

@dp.callback_query(F.data == "back")
async def back(call: CallbackQuery):
    await call.message.edit_text(
        "Asosiy menyu 👇",
        reply_markup=main_menu()
    )
# =================================================

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

@dp.message(Command("users"))
async def export_users(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.append(["User ID", "Username", "Points", "Referrals", "Joined At"])

    for user in users:
        ws.append(user)

    file_name = "users.xlsx"
    wb.save(file_name)

    await message.answer_document(open(file_name, "rb"))

@dp.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    text = message.text.replace("/broadcast ", "")
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent = 0
    for user in users:
        try:
            await bot.send_message(user[0], text)
            sent += 1
        except:
            pass

    await message.answer(f"Yuborildi: {sent} ta userga")
# =================================================

# ================= RUN =================
async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())