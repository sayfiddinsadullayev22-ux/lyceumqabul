import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandStart

# ===== CONFIG =====
TOKEN = "8246098957:AAGtD7OGaD4ThJVGlJM6SSlLkGZ37JV5SY0"
CHANNEL_1 = "@Mirzokhid_blog"
CHANNEL_2 = "@lyceumverse"
WEBINAR_LINK = "https://t.me/+VT0CQQ0n4ag4YzQy"
ADMIN_IDS = [7618889413, 5541894729]
REQUIRED_REFERRALS = 2

bot = Bot(TOKEN)
dp = Dispatcher()

# ===== DATABASE =====
db = sqlite3.connect("bot.db")
cursor = db.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    referrals INTEGER DEFAULT 0,
    referred_by INTEGER
)
""")
db.commit()

# ===== PENDING BROADCASTS =====
pending_broadcasts = {}

# ===== INLINE MENU =====
def main_menu(user_refs=0):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎁 Taklif qilish ({user_refs}/{REQUIRED_REFERRALS})", callback_data="referral")],
        [InlineKeyboardButton(text=f"🎓 Webinar ({user_refs}/{REQUIRED_REFERRALS})", callback_data="webinar")]
    ])

# ===== CHECK SUBS =====
async def check_subscription(user_id):
    try:
        member1 = await bot.get_chat_member(CHANNEL_1, user_id)
        member2 = await bot.get_chat_member(CHANNEL_2, user_id)
        return member1.status != "left" and member2.status != "left"
    except:
        return False

# ===== START =====
@dp.message(CommandStart())
async def start(message: Message, command: CommandStart):
    user_id = message.from_user.id
    args = command.args

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        referred_by = int(args) if args and args.isdigit() and int(args) != user_id else None
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?,?)", (user_id, referred_by))
        db.commit()
        if referred_by:
            cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (referred_by,))
            db.commit()

    cursor.execute("SELECT referrals FROM users WHERE user_id=?", (user_id,))
    refs = cursor.fetchone()[0]

    if not await check_subscription(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1-kanal", url=f"https://t.me/{CHANNEL_1[1:]}")],
            [InlineKeyboardButton(text="2-kanal", url=f"https://t.me/{CHANNEL_2[1:]}")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
        ])
        await message.answer("Iltimos 2 ta kanalga obuna bo‘ling 👇", reply_markup=kb)
        return

    await message.answer(
        "🎉 Ramazon Challenge’ga xush kelibsiz!\n\n"
        "📌 Qoidalar:\n"
        f"1️⃣ Do‘stlarga referral yuboring.\n"
        f"2️⃣ {REQUIRED_REFERRALS} ta referral to‘plaganingizdan keyin Webinar orqali yopiq kanal linkini oling.",
        reply_markup=main_menu(user_refs=refs)
    )

# ===== CHECK SUBS =====
@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT referrals FROM users WHERE user_id=?", (user_id,))
    refs = cursor.fetchone()[0]

    if await check_subscription(user_id):
        await callback.message.answer("Obuna tasdiqlandi ✅", reply_markup=main_menu(user_refs=refs))
    else:
        await callback.answer("Hali obuna bo‘lmagansiz ❌", show_alert=True)

# ===== REFERRAL =====
@dp.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT referrals FROM users WHERE user_id=?", (user_id,))
    refs = cursor.fetchone()[0]
    link = f"https://t.me/lyceumqabulbot?start={user_id}"

    await callback.message.edit_text(
        f"📢 Do‘stlaringizni taklif qiling!\n\n{link}\n\n"
        f"🎁 {REQUIRED_REFERRALS} ta do‘st taklif qiling va yopiq webinar kanaliga kiring!",
        reply_markup=main_menu(user_refs=refs)
    )

# ===== WEBINAR =====
@dp.callback_query(F.data == "webinar")
async def webinar(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT referrals FROM users WHERE user_id=?", (user_id,))
    refs = cursor.fetchone()[0] or 0

    if refs >= REQUIRED_REFERRALS:
        await callback.message.edit_text(
            f"🎓 Sizning referral ballaringiz: {refs}\n"
            f"Webinar linki:\n{WEBINAR_LINK}"
        )
    else:
        remaining = REQUIRED_REFERRALS - refs
        await callback.message.edit_text(
            f"⚠️ Sizning referral ballaringiz: {refs}\n"
            f"Yana {remaining} ta do‘st taklif qiling, shunda webinarga kira olasiz!",
            reply_markup=main_menu(user_refs=refs)
        )

# ===== ADMIN STATS =====
@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(referrals) FROM users")
    total_refs = cursor.fetchone()[0] or 0
    await message.answer(f"👥 Foydalanuvchilar: {total}\n🔗 Jami referral: {total_refs}")

# ===== ADMIN BROADCAST START =====
@dp.message(Command("xabar"))
async def xabar_start(message: Message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        await message.answer("Siz admin emassiz ❌")
        return
    pending_broadcasts[admin_id] = True
    await message.answer("Xabar matnini kiriting. Hammaga yuborish uchun yozing va yuboring:")

# ===== HANDLE BROADCAST TEXT =====
@dp.message()
async def handle_broadcast_text(message: Message):
    admin_id = message.from_user.id
    if admin_id in pending_broadcasts:
        text = message.text
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        count = 0
        for user in users:
            try:
                await bot.send_message(user[0], text)
                count += 1
                if count % 20 == 0:
                    await asyncio.sleep(1)
            except:
                pass
        await message.answer("Xabar hammaga yuborildi ✅")
        pending_broadcasts.pop(admin_id)

# ===== START POLLING =====
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))