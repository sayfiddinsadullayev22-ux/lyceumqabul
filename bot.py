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

bot = Bot(TOKEN)
dp = Dispatcher()

# ===== DATABASE =====
db = sqlite3.connect("bot.db")
cursor = db.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)""")
db.commit()

# ===== INLINE MENU =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Webinar", callback_data="webinar")]
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
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    db.commit()

    if await check_subscription(user_id):
        await message.answer(f"🎓 Siz kanallarga obuna bo‘lgansiz!\nWebinar linki:\n{WEBINAR_LINK}", reply_markup=main_menu())
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1-kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_1[1:]}")],
            [InlineKeyboardButton(text="2-kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_2[1:]}")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
        ])
        await message.answer("Iltimos 2 ta kanalga obuna bo‘ling 👇", reply_markup=kb)

# ===== CHECK SUBS =====
@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        await callback.message.edit_text(f"🎓 Siz kanallarga obuna bo‘lgansiz!\nWebinar linki:\n{WEBINAR_LINK}", reply_markup=main_menu())
    else:
        await callback.answer("Hali obuna bo‘lmagansiz ❌", show_alert=True)

# ===== WEBINAR =====
@dp.callback_query(F.data == "webinar")
async def webinar(callback: CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        await callback.message.edit_text(f"🎓 Webinar linki:\n{WEBINAR_LINK}")
    else:
        await callback.message.edit_text("⚠️ Siz hali 2 ta kanalga obuna bo‘lmadingiz. Iltimos obuna bo‘ling va keyin qayta urinib ko‘ring!")

# ===== ADMIN STATS =====
@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Siz admin emassiz ❌")
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    await message.answer(f"👥 Foydalanuvchilar soni: {total}")

# ===== ADMIN BROADCAST =====
pending_broadcasts = {}

@dp.message(Command("xabar"))
async def xabar_start(message: Message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        await message.answer("Siz admin emassiz ❌")
        return
    pending_broadcasts[admin_id] = True
    await message.answer("Xabar matnini kiriting. Hammaga yuborish uchun yozing va yuboring:")

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
                # Telegram limitini oldini olish uchun har 20 foydalanuvchidan keyin 1 soniya kutadi
                if count % 20 == 0:
                    await asyncio.sleep(1)
            except:
                pass
        await message.answer("✅ Xabar barcha foydalanuvchilarga yuborildi")
        pending_broadcasts.pop(admin_id)

# ===== START POLLING =====
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))