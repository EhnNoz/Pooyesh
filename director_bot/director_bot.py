import os
import re
import sys
import sqlite3
import subprocess
from datetime import datetime

# نصب mutagen در صورت نیاز
try:
    from mutagen import File as MediaFile
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mutagen"])
    from mutagen import File as MediaFile

from balethon import Client

# مسیر پوشه‌های دسته‌بندی شده برای فایل‌ها
UPLOAD_ROOT = "uploads"
for f in ["video", "image", "text", "audio", "other"]:
    os.makedirs(os.path.join(UPLOAD_ROOT, f), exist_ok=True)

# اتصال به دیتابیس
if os.path.exists("data.db"):
    os.remove("data.db")

conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    username TEXT,
    full_name TEXT,
    city TEXT,
    language_code TEXT,
    is_bot BOOLEAN,
    role TEXT,
    sub_role TEXT,
    age INTEGER,
    phone_number TEXT,
    sample_type TEXT,
    sample_text TEXT,
    file_path TEXT,
    file_duration TEXT,
    message_date TEXT,
    message_id INTEGER
)
""")
conn.commit()

# توکن بات
TOKEN = "2136694931:ac29epH3lKrG2n7gUzEtmyv1l9IXrRkPhBK4VwqV"
bot = Client(TOKEN)
user_states = {}

# ترتیب مراحل فرم
step_order = ["role", "full_name", "city", "age", "phone", "sample_type", "sample_input"]

# 🎛️ کیبوردهای اصلی و فرعی
back_keyboard = {
    "keyboard": [["↩️ بازگشت", "🔄 شروع مجدد"]],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

roles_keyboard = {
    "keyboard": [
        ["تهیه کننده", "نویسنده"],
        ["کارگردان", "تدوینگر"],
        ["↩️ بازگشت", "🔄 شروع مجدد"]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

# کیبوردهای فرعی برای هر نقش
producer_submenu = {
    "keyboard": [
        ["زیرمنوی دو تهیه کننده", "زیرمنوی یک تهیه کننده"],
        ["زیرمنوی چهار تهیه کننده", "زیرمنوی سه تهیه کننده"],
        ["↩️ بازگشت به انتخاب نقش", "🔄 شروع مجدد"]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

writer_submenu = {
    "keyboard": [
        ["زیرمنوی دو نویسنده", "زیرمنوی یک نویسنده"],
        ["زیرمنوی چهار نویسنده", "زیرمنوی سه نویسنده"],
        ["↩️ بازگشت به انتخاب نقش", "🔄 شروع مجدد"]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

director_submenu = {
    "keyboard": [
        ["زیرمنوی دو کارگردان", "زیرمنوی یک کارگردان"],
        ["زیرمنوی چهار کارگردان", "زیرمنوی سه کارگردان"],
        ["↩️ بازگشت به انتخاب نقش", "🔄 شروع مجدد"]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

editor_submenu = {
    "keyboard": [
        ["زیرمنوی دو تدوینگر", "زیرمنوی یک تدوینگر"],
        ["زیرمنوی چهار تدوینگر", "زیرمنوی سه تدوینگر"],
        ["↩️ بازگشت به انتخاب نقش", "🔄 شروع مجدد"]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

sample_type_keyboard = {
    "keyboard": [
        ["متن"], ["فایل تصویری"], ["فایل صوتی"],
        ["فایل ویدیویی"], ["فایل متنی"],
        ["↩️ بازگشت", "🔄 شروع مجدد"]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True
}


# ✅ اعتبارسنجی‌های مرحله‌ای
def is_persian(text):
    return bool(re.fullmatch(r"[آ-ی‌\s]+", text.strip()))


def is_valid_age(text):
    return text.isdigit() and 1 <= int(text) <= 99


def is_valid_phone(text):
    digits = re.sub(r"\D", "", text)
    return len(digits) >= 11


# تابع برای تشخیص زیرمنوها
def is_submenu_option(text):
    submenu_options = [
        "زیرمنوی یک تهیه کننده", "زیرمنوی دو تهیه کننده", "زیرمنوی سه تهیه کننده", "زیرمنوی چهار تهیه کننده",
        "زیرمنوی یک نویسنده", "زیرمنوی دو نویسنده", "زیرمنوی سه نویسنده", "زیرمنوی چهار نویسنده",
        "زیرمنوی یک کارگردان", "زیرمنوی دو کارگردان", "زیرمنوی سه کارگردان", "زیرمنوی چهار کارگردان",
        "زیرمنوی یک تدوینگر", "زیرمنوی دو تدوینگر", "زیرمنوی سه تدوینگر", "زیرمنوی چهار تدوینگر"
    ]
    return text in submenu_options


# 🎬 استخراج متادیتای فایل (مدت زمان ویدیویی یا صوتی)
def extract_metadata(path):
    try:
        media = MediaFile(path)
        duration = media.info.length
        return str(round(duration)) + "s" if duration else None
    except Exception:
        return None


@bot.on_message()
async def handle_message(client, message):
    chat_id = message.chat.id
    user = message.author
    text = (message.text or "").strip()
    user_data = user_states.get(chat_id, {})

    print(f"[📨 پیام دریافت شد از {chat_id}]: {text}")

    # 🔄 شروع مجدد
    if text == "/start" or text == "🔄 شروع مجدد":
        user_states[chat_id] = {"step": "role"}
        await message.reply("🎭 لطفاً نقش حرفه‌ای خود را انتخاب فرمایید:", reply_markup=roles_keyboard)
        return

    if text == "↩️ بازگشت":
        current_step = user_data.get("step")
        if current_step and current_step in step_order:
            idx = step_order.index(current_step)
            if idx > 0:
                prev_step = step_order[idx - 1]
                user_data["step"] = prev_step
                user_states[chat_id] = user_data

                # تبدیل نام مرحله به فارسی برای پیام
                step_names = {
                    "role": "نقش",
                    "full_name": "نام کامل",
                    "city": "شهر",
                    "age": "سن",
                    "phone": "شماره تلفن",
                    "sample_type": "نوع نمونه کار",
                    "sample_input": "ورودی نمونه کار"
                }
                persian_step_name = step_names.get(prev_step, prev_step)

                await message.reply(f"↩️ لطفاً مرحله *{persian_step_name}* را مجدداً وارد نمایید:",
                                    reply_markup=back_keyboard)
            else:
                await message.reply("⚠️ مرحله قبلی موجود نیست.")
        return

    # ↩️ بازگشت به انتخاب نقش
    if text == "↩️ بازگشت به انتخاب نقش":
        user_data["step"] = "role"
        user_states[chat_id] = user_data
        await message.reply("🎭 لطفاً نقش حرفه‌ای خود را انتخاب فرمایید:", reply_markup=roles_keyboard)
        return

    # پردازش زیرمنوها
    if is_submenu_option(text):
        # تعیین نقش اصلی بر اساس زیرمنوی انتخاب شده
        if "تهیه کننده" in text:
            user_data["role"] = "تهیه کننده"
        elif "نویسنده" in text:
            user_data["role"] = "نویسنده"
        elif "کارگردان" in text:
            user_data["role"] = "کارگردان"
        elif "تدوینگر" in text:
            user_data["role"] = "تدوینگر"

        # ذخیره زیرمنوی انتخاب شده به عنوان تخصص
        user_data["sub_role"] = text

        # انتقال مستقیم به مرحله وارد کردن نام
        user_data["step"] = "full_name"
        user_states[chat_id] = user_data
        await message.reply("🧒 لطفاً نام و نام خانوادگی خود را فقط به فارسی وارد فرمایید:", reply_markup=back_keyboard)
        return

    # 📎 دریافت فایل
    if hasattr(message, "document") and user_data.get("step") == "sample_input":
        original_filename = message.document.name or "file.unknown"
        mime = message.document.mime_type or ""
        mime_main = mime.split("/")[0]
        folder = {
            "video": "video", "image": "image", "text": "text",
            "application": "text", "audio": "audio"
        }.get(mime_main, "other")
        full_path = os.path.join(UPLOAD_ROOT, folder, f"{chat_id}_{original_filename}")

        response = await client.download(message.document.id)
        with open(full_path, "wb") as f:
            f.write(response)

        user_data["file_path"] = full_path
        user_data["file_duration"] = extract_metadata(full_path)
        user_data["message_date"] = datetime.fromtimestamp(message.date.timestamp()).isoformat()
        user_data["message_id"] = message.id

        cursor.execute("""
            INSERT INTO submissions (
                chat_id, username, full_name, city, language_code, is_bot,
                role, sub_role, age, phone_number, sample_type, sample_text,
                file_path, file_duration, message_date, message_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user.id, user.username, user_data["full_name"], user_data["city"],
            user.language_code, user.is_bot, user_data["role"], user_data.get("sub_role"),
            user_data["age"], user_data["phone"], user_data["sample_type"], None,
            user_data["file_path"], user_data["file_duration"],
            user_data["message_date"], user_data["message_id"]
        ))
        conn.commit()

        await message.reply("✅ فایل شما با موفقیت دریافت و ثبت شد.\n🙏 از همکاری شما صمیمانه سپاسگزاریم.")
        user_states[chat_id] = {}
        return

    # 📝 دریافت متن نمونه‌کار
    if user_data.get("step") == "sample_input" and user_data.get("sample_type") == "متن":
        user_data["sample_text"] = text
        user_data["message_date"] = datetime.fromtimestamp(message.date.timestamp()).isoformat()
        user_data["message_id"] = message.id

        cursor.execute("""
            INSERT INTO submissions (
                chat_id, username, full_name, city, language_code, is_bot,
                role, sub_role, age, phone_number, sample_type, sample_text,
                message_date, message_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user.id, user.username, user_data["full_name"], user_data["city"],
            user.language_code, user.is_bot, user_data["role"], user_data.get("sub_role"),
            user_data["age"], user_data["phone"], user_data["sample_type"], user_data["sample_text"],
            user_data["message_date"], user_data["message_id"]
        ))
        conn.commit()

        await message.reply("✅ نمونه‌کار متنی شما با موفقیت ثبت شد.\n🙏 از همراهی شما متشکریم.")
        user_states[chat_id] = {}
        return

    # 🎯 مراحل فرم مرحله‌ای
    step = user_data.get("step")

    if step == "role":
        user_data["role"] = text
        # نمایش منوی فرعی بر اساس نقش انتخاب شده
        if text == "تهیه کننده":
            await message.reply("لطفاً تخصص خود را انتخاب کنید:", reply_markup=producer_submenu)
        elif text == "نویسنده":
            await message.reply("لطفاً تخصص خود را انتخاب کنید:", reply_markup=writer_submenu)
        elif text == "کارگردان":
            await message.reply("لطفاً تخصص خود را انتخاب کنید:", reply_markup=director_submenu)
        elif text == "تدوینگر":
            await message.reply("لطفاً تخصص خود را انتخاب کنید:", reply_markup=editor_submenu)
        else:
            user_data["step"] = "full_name"
            await message.reply("🧒 لطفاً نام و نام خانوادگی خود را فقط به فارسی وارد فرمایید:", reply_markup=back_keyboard)

    elif step == "full_name":
        if not is_persian(text):
            await message.reply("⚠️ لطفاً نام را فقط با حروف فارسی وارد کنید.", reply_markup=back_keyboard)
            return
        user_data["full_name"] = text
        user_data["step"] = "city"
        await message.reply("🏙️ لطفاً شهر محل سکونت خود را وارد فرمایید:",
                            reply_markup=back_keyboard)
    elif step == "city":
        if not text:
            await message.reply("⚠️ لطفاً شهر خود را وارد کنید.", reply_markup=back_keyboard)
            return
        user_data["city"] = text
        user_data["step"] = "age"
        await message.reply("🎂 لطفاً سن خود را بصورت عددی وارد فرمایید:", reply_markup=back_keyboard)
    elif step == "age":
        if not is_valid_age(text):
            await message.reply("⚠️ عدد واردشده صحیح نیست.",
                                reply_markup=back_keyboard)
            return
        user_data["age"] = int(text)
        user_data["step"] = "phone"
        await message.reply(
            "📱 لطفاً شماره تلفن همراه خود را وارد فرمایید.\nنمونه‌های صحیح:\n - 09123456789\n - +989123456789\n - 989123456789",
            reply_markup=back_keyboard)
    elif step == "phone":
        if not is_valid_phone(text):
            await message.reply("⚠️ شماره تلفن معتبر نیست. باید حداقل ۱۱ رقم باشد.", reply_markup=back_keyboard)
            return
        user_data["phone"] = text
        user_data["step"] = "sample_type"
        await message.reply("📎 لطفاً نوع نمونه‌کار را انتخاب فرمایید:", reply_markup=sample_type_keyboard)
    elif step == "sample_type":
        user_data["sample_type"] = text
        user_data["step"] = "sample_input"

        prompt_map = {
            "متن": "📝 لطفاً نمونه‌کار متنی خود را ارسال فرمایید:",
            "فایل تصویری": "🖼 لطفاً فایل تصویری خود را ارسال فرمایید.",
            "فایل صوتی": "🎵 لطفاً فایل صوتی خود را ارسال فرمایید.",
            "فایل ویدیویی": "🎬 لطفاً فایل ویدیویی خود را ارسال فرمایید.",
            "فایل متنی": "📄 لطفاً فایل متنی خود را ارسال فرمایید."
        }
        prompt = prompt_map.get(text, "📎 لطفاً فایل خود را ارسال فرمایید.")
        await message.reply(prompt, reply_markup=back_keyboard)

    user_states[chat_id] = user_data


print("🚀 بات با موفقیت اجرا شد و آماده دریافت اطلاعات کاربران محترم است...")
bot.run()