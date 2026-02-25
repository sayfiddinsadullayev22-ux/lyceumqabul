import asyncio
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
    if await check_subscription(user_id):
        # Foydalanuvchi obuna → webinar linki
        await message.answer(f"🎓 Siz kanallarga obuna bo‘lgansiz!\nWebinar linki:\n{WEBINAR_LINK}", reply_markup=main_menu())
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1-kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_1[1:]}")],
            [InlineKeyboardButton(text="2-kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_2[1:]}")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
        ])
        await message.answer("Iltimos 2 ta kanalga obuna bo‘ling 👇", reply_markup=kb)

# ===== CHECK SUBS CALLBACK =====
@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        await callback.message.edit_text(f"🎓 Siz kanallarga obuna bo‘lgansiz!\nWebinar linki:\n{WEBINAR_LINK}", reply_markup=main_menu())
    else:
        await callback.answer("Hali obuna bo‘lmagansiz ❌", show_alert=True)

# ===== WEBINAR CALLBACK =====
@dp.callback_query(F.data == "webinar")
async def webinar(callback: CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        await callback.message.edit_text(f"🎓 Webinar linki:\n{WEBINAR_LINK}")
    else:
        await callback.message.edit_text("⚠️ Siz hali 2 ta kanalga obuna bo‘lmadingiz. Iltimos obuna bo‘ling va keyin qayta urinib ko‘ring!")

# ===== ADMIN STATS & BROADCAST =====
@dp.message(commands=["stats"])
async def stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Foydalanuvchi statistikasi hozircha yo‘q (referral olib tashlandi)")

@dp.message(commands=["xabar"])
async def xabar_start(message: Message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        await message.answer("Siz admin emassiz ❌")
        return
    await message.answer("Xabar matnini yozing. Hammaga yuborish uchun yuboring:")
    pending_broadcasts[admin_id] = True

pending_broadcasts = {}

@dp.message()
async def handle_broadcast_text(message: Message):
    admin_id = message.from_user.id
    if admin_id in pending_broadcasts:
        text = message.text
        await bot.send_message(ADMIN_IDS[0], f"Hammaga yuboriladigan xabar: {text}")
        pending_broadcasts.pop(admin_id)

# ===== START POLLING =====
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))