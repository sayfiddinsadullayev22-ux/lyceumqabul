import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandStart

TOKEN = "8246098957:AAGtD7OGaD4ThJVGlJM6SSlLkGZ37JV5SY0"
CHANNEL_1 = "@Mirzokhid_blog"
CHANNEL_2 = "@lyceumverse"
WEBINAR_LINK = "https://t.me/+VT0CQQ0n4ag4YzQy"

ADMIN_IDS = [7618889413 , 5541894729]

bot = Bot(TOKEN)
dp = Dispatcher()

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


async def check_subscription(user_id):
    try:
        member1 = await bot.get_chat_member(CHANNEL_1, user_id)
        member2 = await bot.get_chat_member(CHANNEL_2, user_id)
        return member1.status != "left" and member2.status != "left"
    except:
        return False


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Taklif qilish", callback_data="referral")],
        [InlineKeyboardButton(text="🎓 Webinar", callback_data="webinar")]
    ])


@dp.message(CommandStart())
async def start(message: Message, command: CommandStart):
    user_id = message.from_user.id
    args = command.args

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        referred_by = int(args) if args and args.isdigit() and int(args) != user_id else None
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?,?)",
                       (user_id, referred_by))
        db.commit()

        if referred_by:
            cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?",
                           (referred_by,))
            db.commit()

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
        "1️⃣ Do‘stlarga referral yuboring.\n"
        "2️⃣ 2 ta referral to‘plaganingizdan keyin Webinar orqali yopiq kanal linkini oling.",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.answer("Obuna tasdiqlandi ✅", reply_markup=main_menu())
    else:
        await callback.answer("Hali obuna bo‘lmagansiz ❌", show_alert=True)


@dp.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery):
    link = f"https://t.me/YOUR_BOT?start={callback.from_user.id}"
    await callback.message.answer(
        f"📢 Do‘stlaringizni taklif qiling!\n\n{link}"
    )


@dp.callback_query(F.data == "webinar")
async def webinar(callback: CallbackQuery):
    cursor.execute("SELECT referrals FROM users WHERE user_id=?",
                   (callback.from_user.id,))
    refs = cursor.fetchone()[0]

    if refs >= 2:
        await callback.message.answer(f"🎓 Webinar linki:\n{WEBINAR_LINK}")
    else:
        await callback.answer("Sizda hali 2 ta referral yo‘q ❌", show_alert=True)


@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(referrals) FROM users")
    total_refs = cursor.fetchone()[0] or 0

    await message.answer(
        f"👥 Foydalanuvchilar: {total}\n"
        f"🔗 Jami referral: {total_refs}"
    )


@dp.message(Command("xabar"))
async def broadcast(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    text = message.text.replace("/xabar ", "")
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

    await message.answer("Xabar yuborildi ✅")


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))