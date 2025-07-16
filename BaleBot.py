from balethon.objects import InlineKeyboard, InlineKeyboardButton, ReplyKeyboardButton, ReplyKeyboard
from balethon import Client
from balethon.conditions import private
import os
import logging
# logging.basicConfig(level=logging.INFO)

bot = Client("388773998:FOyKJ2cDpOC7LnG4NL5Dl5eg8ou7zC3VyDPWp7B9")

if not os.path.exists('user_uploads'):
    os.makedirs('user_uploads')

# منوی اصلی
main_menu = InlineKeyboard(
    [InlineKeyboardButton("تهیه کننده", callback_data="producer")],
    [InlineKeyboardButton("تدوینگر", callback_data="editor")],
    [InlineKeyboardButton("فیلمبردار", callback_data="cameraman")],
    [InlineKeyboardButton("نویسنده", callback_data="writer")]
)

# زیرمنوها
sub_menus = {
    "producer": InlineKeyboard(
        [InlineKeyboardButton("تولیدی", callback_data="producer_production")],
        [InlineKeyboardButton("تأمینی", callback_data="producer_supply")]
    ),
    "editor": InlineKeyboard(
        [InlineKeyboardButton("حرفه‌ای", callback_data="editor_pro")],
        [InlineKeyboardButton("نیمه‌حرفه‌ای", callback_data="editor_semi")]
    ),
    "cameraman": InlineKeyboard(
        [InlineKeyboardButton("حرفه‌ای", callback_data="cameraman_pro")],
        [InlineKeyboardButton("نیمه‌حرفه‌ای", callback_data="cameraman_semi")]
    ),
    "writer": InlineKeyboard(
        [InlineKeyboardButton("داستان", callback_data="writer_story")],
        [InlineKeyboardButton("شعر", callback_data="writer_poem")]
    )
}

# ذخیره موقت اطلاعات کاربر
user_data = {}


@bot.on_message(private)
async def handle_message(message):
    user_id = message.author.id

    if user_id in user_data:
        current_step = user_data[user_id]["step"]

        if current_step == "name":
            user_data[user_id]["name"] = message.text
            user_data[user_id]["step"] = "experience"
            await message.reply("لطفاً سابقه کار خود را بنویسید:")
            return

        elif current_step == "experience":
            user_data[user_id]["experience"] = message.text
            user_data[user_id]["step"] = "portfolio"
            await message.reply("لطفاً نمونه کارتان را آپلود یا لینک دهید:")
            return

        elif current_step == "portfolio":
            # دریافت نمونه کار (متن یا فایل)
            if message.text:
                portfolio = message.text
            elif message.document:
                # روش سازگار با Balethon برای دریافت اطلاعات فایل
                file_id = message.document.id  # در Balethon ممکن است file_id به این شکل باشد
                file_name = getattr(message.document, 'file_name', getattr(message.document, 'name', 'بدون نام'))
                portfolio = f"فایل: {file_name} (ID: {file_id})"
            elif message.photo:
                # برای عکس‌ها در Balethon
                photo = message.photo[-1] if isinstance(message.photo, list) else message.photo
                portfolio = f"عکس (ID: {photo.id})"
            elif message.video:
                portfolio = f"ویدئو (ID: {message.video.id})"
            else:
                portfolio = "بدون نمونه کار"

            user_data[user_id]["portfolio"] = portfolio
            role = user_data[user_id]["role"]
            sub_role = user_data[user_id]["sub_role"]
            name = user_data[user_id]["name"]
            experience = user_data[user_id]["experience"]

            # چاپ لاگ نهایی
            print(f"✅ Final Data Submitted by User {user_id}:")
            print(f"Role: {role}")
            print(f"Sub-role: {sub_role}")
            print(f"Name: {name}")
            print(f"Experience: {experience}")
            print(f"Portfolio: {portfolio}")

            await message.reply(
                f"✅ اطلاعات شما ثبت شد:\n\n"
                f"📌 نقش: {role}\n"
                f"🔹 تخصص: {sub_role}\n"
                f"👤 نام: {name}\n"
                f"📅 سابقه کار: {experience}\n"
                f"📂 نمونه کار: {portfolio}\n\n"
                "متشکرم! به زودی با شما تماس می‌گیریم."
            )
            del user_data[user_id]
            return

    await message.reply("👋 سلام! لطفاً نقش خود را انتخاب کنید:", reply_markup=main_menu)


@bot.on_callback_query()
async def handle_callback_query(callback_query):
    user_id = callback_query.author.id
    data = callback_query.data

    role_map = {
        "producer": "تهیه کننده",
        "editor": "تدوینگر",
        "cameraman": "فیلمبردار",
        "writer": "نویسنده"
    }

    sub_role_map = {
        "producer_production": "تولیدی",
        "producer_supply": "تأمینی",
        "editor_pro": "حرفه‌ای",
        "editor_semi": "نیمه‌حرفه‌ای",
        "cameraman_pro": "حرفه‌ای",
        "cameraman_semi": "نیمه‌حرفه‌ای",
        "writer_story": "داستان",
        "writer_poem": "شعر"
    }

    if data in role_map:
        user_data[user_id] = {
            "role": role_map[data],
            "step": "sub_role"
        }
        await callback_query.answer(text=f"نقش {role_map[data]} انتخاب شد")

        # ویرایش پیام فعلی با زیرمنو
        await bot.send_message(
            chat_id=callback_query.message.chat.id,
            text="لطفاً تخصص خود را انتخاب کنید:",
            reply_markup=sub_menus[data]
        )

    elif data in sub_role_map:
        user_data[user_id]["sub_role"] = sub_role_map[data]
        user_data[user_id]["step"] = "name"
        await callback_query.answer(text=f"تخصص {sub_role_map[data]} انتخاب شد")
        await bot.send_message(
            chat_id=callback_query.message.chat.id,
            text="لطفاً نام کامل خود را وارد کنید:"
        )



bot.run()