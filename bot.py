import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ====================================
# BU YERGA BOTFATHER DAN OLINGAN YANGI TOKENNI QO'YING
# ====================================
TOKEN = "8246098957:AAGtD7OGaD4ThJVGlJM6SSlLkGZ37JV5SY0"

CHANNEL_1 = "@lyceumverse"
CHANNEL_2 = "@Mirzokhid_blog"

INSTAGRAM_URL = "https://www.instagram.com/_mirzokh1d?igsh=MXF0Z2F3ZmZjMnI1dQ=="

WEBINAR_LINK = "https://example.com/webinar"
NEEDED_POINTS = 5

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==========================
# DATABASE
# ==========================
db = sqlite3.connect("users.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS invites (
    user_id INTEGER PRIMARY KEY,
    invited_by INTEGER
)
""")

db.commit()


def add_user(user_id: int):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, points, referrals) VALUES (?, 0, 0)",
        (user_id,)
    )
    db.commit()


def get_user(user_id: int):
    cursor.execute("SELECT points, referrals FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()


def add_points(user_id: int, amount: int = 1):
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id=?", (amount, user_id))
    db.commit()


def add_referral_count(user_id: int):
    cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (user_id,))
    db.commit()


def has_invite(user_id: int):
    cursor.execute("SELECT invited_by FROM invites WHERE user_id=?", (user_id,))
    return cursor.fetchone()


def save_invite(user_id: int, invited_by: int):
    cursor.execute("INSERT OR IGNORE INTO invites (user_id, invited_by) VALUES (?, ?)", (user_id, invited_by))
    db.commit()


# ==========================
# KEYBOARDS
# ==========================
def subscribe_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Lyceumverse", url="https://t.me/lyceumverse")
    kb.button(text="📢 Mirzokhid Blog", url="https://t.me/Mirzokhid_blog")
    kb.button(text="📸 Instagram", url=INSTAGRAM_URL)
    kb.button(text="✅ Tekshirish", callback_data="check_sub")
    kb.adjust(1)
    return kb.as_markup()


def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Profilim", callback_data="profile")
    kb.button(text="🎁 Referal", callback_data="referral")
    kb.button(text="🎥 Vebinar", callback_data="webinar")
    kb.adjust(2, 1)
    return kb.as_markup()


def back_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Orqaga", callback_data="back")
    return kb.as_markup()


def webinar_link_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎥 Webinarni ochish", url=WEBINAR_LINK)
    kb.button(text="⬅️ Orqaga", callback_data="back")
    kb.adjust(1)
    return kb.as_markup()


def referral_button():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Referal olish", callback_data="referral")
    kb.button(text="⬅️ Orqaga", callback_data="back")
    kb.adjust(1)
    return kb.as_markup()


# ==========================
# SUBSCRIPTION CHECK
# ==========================
async def check_subscription(user_id: int):
    try:
        member1 = await bot.get_chat_member(CHANNEL_1, user_id)
        member2 = await bot.get_chat_member(CHANNEL_2, user_id)

        ok1 = member1.status in ["member", "administrator", "creator"]
        ok2 = member2.status in ["member", "administrator", "creator"]

        return ok1 and ok2
    except:
        return False


# ==========================
# START COMMAND
# ==========================
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    add_user(user_id)

    args = message.text.split()

    # referral ishlashi
    if len(args) > 1:
        ref_id = args[1]

        if ref_id.isdigit():
            ref_id = int(ref_id)

            if ref_id != user_id:
                add_user(ref_id)

                if not has_invite(user_id):
                    save_invite(user_id, ref_id)
                    add_points(ref_id, 1)
                    add_referral_count(ref_id)

    is_sub = await check_subscription(user_id)

    if not is_sub:
        await message.answer(
            "👋 Assalomu alaykum!\n\n"
            "Botdan foydalanish uchun quyidagilarga obuna bo‘ling:\n\n"
            "✅ Telegram kanallar\n"
            "⚠️ Admin hammasini tekshiradi (faqat link)\n\n"
            "Obuna bo‘lgach pastdagi tugmani bosing:",
            reply_markup=subscribe_keyboard()
        )
    else:
        await message.answer(
            "🎉 Xush kelibsiz!\n\n"
            "Siz muvaffaqiyatli obuna bo‘ldingiz.\n"
            "Quyidagi menyudan foydalaning:",
            reply_markup=main_menu()
        )


# ==========================
# CHECK SUB BUTTON
# ==========================
@dp.callback_query(F.data == "check_sub")
async def check_sub_handler(call: CallbackQuery):
    user_id = call.from_user.id
    is_sub = await check_subscription(user_id)

    if is_sub:
        await call.message.edit_text(
            "🎉 Obuna tasdiqlandi!\n\n"
            "Endi botdan foydalanishingiz mumkin:",
            reply_markup=main_menu()
        )
    else:
        await call.answer("❌ Hali ham Telegram kanallarga obuna bo‘lmagansiz!", show_alert=True)


# ==========================
# BACK BUTTON
# ==========================
@dp.callback_query(F.data == "back")
async def back_handler(call: CallbackQuery):
    await call.message.edit_text("🏠 Asosiy menyu:", reply_markup=main_menu())


# ==========================
# PROFILE
# ==========================
@dp.callback_query(F.data == "profile")
async def profile_handler(call: CallbackQuery):
    user_id = call.from_user.id
    points, referrals = get_user(user_id)

    await call.message.edit_text(
        f"👤 Profilingiz:\n\n"
        f"⭐ Ball: {points}\n"
        f"👥 Referallar: {referrals}\n\n"
        f"📌 Har 1 referal = 1 ball",
        reply_markup=back_menu()
    )


# ==========================
# REFERRAL
# ==========================
@dp.callback_query(F.data == "referral")
async def referral_handler(call: CallbackQuery):
    user_id = call.from_user.id
    bot_username = (await bot.get_me()).username

    referral_link = f"https://t.me/{bot_username}?start={user_id}"

    await call.message.edit_text(
        f"🎁 Referal tizimi:\n\n"
        f"📌 Har bir odam sizning referalingiz orqali kirsa — 1 ball olasiz.\n\n"
        f"🔗 Sizning referal linkingiz:\n\n"
        f"{referral_link}\n\n"
        f"📤 Do‘stlaringizga ulashing!",
        reply_markup=back_menu()
    )


# ==========================
# WEBINAR
# ==========================
@dp.callback_query(F.data == "webinar")
async def webinar_handler(call: CallbackQuery):
    user_id = call.from_user.id
    points, _ = get_user(user_id)

    if points >= NEEDED_POINTS:
        await call.message.edit_text(
            "🎥 Sizda yetarli ball bor!\n\n"
            "Webinar havolasi quyida:",
            reply_markup=webinar_link_keyboard()
        )
    else:
        need = NEEDED_POINTS - points
        await call.message.edit_text(
            f"❌ Sizda yetarli ball yo‘q.\n\n"
            f"⭐ Hozirgi ball: {points}\n"
            f"🎯 Kerakli ball: {NEEDED_POINTS}\n"
            f"📌 Yetishmayapti: {need} ball\n\n"
            f"Ball yig‘ish uchun referal ulashing:",
            reply_markup=referral_button()
        )


# ==========================
# RUN
# ==========================
async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
