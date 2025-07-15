from balethon.objects import InlineKeyboard, InlineKeyboardButton
from balethon import Client
from balethon.conditions import private

bot = Client("2136694931:ac29epH3lKrG2n7gUzEtmyv1l9IXrRkPhBK4VwqV")

# منوی اصلی
main_menu = InlineKeyboard(
    [InlineKeyboardButton("تهیه کننده", callback_data="producer")],
    [InlineKeyboardButton("تدوینگر", callback_data="editor")],
    [InlineKeyboardButton("فیلمبردار", callback_data="cameraman")],
    [InlineKeyboardButton("نویسنده", callback_data="writer")]
)

# ذخیره موقت اطلاعات کاربر
user_data = {}  # {user_id: {'role': '', 'step': '', ...}}


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
            user_data[user_id]["portfolio"] = message.text
            role = user_data[user_id]["role"]
            name = user_data[user_id]["name"]
            experience = user_data[user_id]["experience"]
            portfolio = user_data[user_id]["portfolio"]

            await message.reply(
                f"✅ اطلاعات شما ثبت شد:\n\n"
                f"📌 نقش: {role}\n"
                f"👤 نام: {name}\n"
                f"📅 سابقه کار: {experience}\n"
                # f"🎥 نمونه کار: {portfolio}\n\n"
                "متشکرم! به زودی با شما تماس می‌گیریم."
            )
            del user_data[user_id]
            return

    await message.reply("👋 سلام! لطفاً نقش خود را انتخاب کنید:", reply_markup=main_menu)


@bot.on_callback_query()
async def handle_callback_query(callback_query):
    user_id = callback_query.author.id  # تغییر از from_user به author
    role_map = {
        "producer": "تهیه کننده",
        "editor": "تدوینگر",
        "cameraman": "فیلمبردار",
        "writer": "نویسنده"
    }

    if callback_query.data in role_map:
        user_data[user_id] = {
            "role": role_map[callback_query.data],
            "step": "name"
        }

        await callback_query.answer(text="نقش شما انتخاب شد!")
        await callback_query.message.reply("لطفاً نام کامل خود را وارد کنید:")


bot.run()