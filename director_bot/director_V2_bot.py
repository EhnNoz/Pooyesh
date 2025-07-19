import os
import subprocess
import sys
from datetime import datetime
import requests
from balethon import Client
import psycopg2
from psycopg2 import sql

# 📦 ساخت پوشه‌های آپلود
UPLOAD_ROOT = "uploads"
for folder in ["video", "image", "text", "audio", "other"]:
    os.makedirs(os.path.join(UPLOAD_ROOT, folder), exist_ok=True)


# 🗄️ اتصال به PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        host="",
        database="",
        user="",
        password="",
        port="5432"
    )


# ایجاد جدول اگر وجود نداشته باشد
def create_table():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            username TEXT,
            role TEXT,
            subrole TEXT,
            gender TEXT,
            age_range TEXT,
            province TEXT,
            sample_type TEXT,
            file_path TEXT,
            file_size TEXT,
            phone_number TEXT,
            message_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        if conn:
            conn.close()


create_table()

# 🤖 راه‌اندازی ربات بله
TOKEN = ""
bot = Client(TOKEN)
user_states = {}


# 🟢 پیام آغاز
def set_start_message():
    text = (
        "🗂️ به «سامانه پویش» خوش آمدید!\n\n"
        "در این سامانه می‌توانید نمونه‌کارهای خود را در قالب‌های ویدیویی، تصویری، صوتی و متنی ارسال فرمایید.\n"
        "برای آغاز، لطفاً دکمه «شروع» را فشار دهید 👇"
    )
    try:
        requests.post(
            f"https://tapi.bale.ai/bot{TOKEN}/setStartMessage",
            headers={"Content-Type": "application/json"},
            json={"text": text}
        )
        print("✅ پیام آغاز تنظیم شد")
    except Exception as e:
        print("⚠️ خطا در تنظیم پیام آغاز:", e)


set_start_message()

# ⌨️ کیبوردهای عمومی
start_keyboard = {
    "keyboard": [["شروع"]],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

final_keyboard = {
    "keyboard": [["🔄 شروع مجدد"]],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

phone_keyboard = {
    "keyboard": [[{"text": "ارسال شماره", "request_contact": True}], ["↩️ بازگشت"], ["🔄 شروع مجدد"]],
    "resize_keyboard": True,
    "one_time_keyboard": True
}

# 🎭 نقش‌ها و ریزنقش‌ها
roles = ["تهیه کننده", "نویسنده", "کارگردان", "تدوینگر"]
subroles = {role: [f"{role} {i}" for i in range(1, 7)] for role in roles}

# 👤 جنسیت
gender_options = ["زن", "مرد"]

# 🎂 محدوده سنی
age_ranges = [
    "زیر ۱۸ سال", "۱۸ تا ۲۵ سال", "۲۶ تا ۳۵ سال",
    "۳۶ تا ۴۵ سال", "۴۶ تا ۶۰ سال", "بیشتر از ۶۰ سال"
]

# � استان‌ها
provinces = [
    "آذربایجان شرقی", "آذربایجان غربی", "اردبیل", "اصفهان", "البرز", "ایلام", "بوشهر", "تهران",
    "چهارمحال و بختیاری", "خراسان جنوبی", "خراسان رضوی", "خراسان شمالی", "خوزستان", "زنجان",
    "سمنان", "سیستان و بلوچستان", "فارس", "قزوین", "قم", "کردستان", "کرمان", "کرمانشاه",
    "کهگیلویه و بویراحمد", "گلستان", "گیلان", "لرستان", "مازندران", "مرکزی", "هرمزگان", "همدان", "یزد"
]

# 📎 نوع نمونه‌کار
sample_types = {
    "فایل ویدیویی 🎬": "MP4, MOV, MKV, AVI",
    "فایل صوتی 🎵": "MP3, WAV, AAC, OGG",
    "فایل تصویری 🖼️": "JPG, PNG",
    "فایل متنی 📄": "PDF, DOCX"
}


# 📦 حجم فایل
def file_size(path):
    try:
        size_kb = round(os.path.getsize(path) / 1024)
        return f"{size_kb} KB" if size_kb < 1024 else f"{round(size_kb / 1024, 1)} MB"
    except:
        return "نامشخص"


# 🔧 ساخت کیبورد سفارشی
def make_keyboard(items, per_row=2, include_back=True):
    rows = [items[i:i + per_row] for i in range(0, len(items), per_row)]
    if include_back:
        rows += [["↩️ بازگشت"], ["🔄 شروع مجدد"]]
    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "one_time_keyboard": True
    }


@bot.on_message()
async def handle_message(client, message):
    chat_id = message.chat.id
    user = message.author
    username = user.username or user.full_name or str(user.id)
    text = (message.text or "").strip()
    state = user_states.get(chat_id, {})
    step = state.get("step")

    if text in ["/start", "شروع", "🔄 شروع مجدد"]:
        user_states[chat_id] = {"step": "role"}
        await message.reply("🎭 نقش خود را انتخاب کنید:",
                            reply_markup=make_keyboard(roles, per_row=2, include_back=False))
        return

    if text == "↩️ بازگشت":
        previous_steps = {
            "subrole": "role", "gender": "subrole", "age_range": "gender",
            "province": "age_range", "phone": "province", "sample_type": "phone"
        }
        if step in previous_steps:
            state["step"] = previous_steps[step]
            user_states[chat_id] = state
            prompts = {
                "role": "🎭 نقش خود را انتخاب کنید:",
                "subrole": f"🎯 یکی از ریزنقش‌های «{state.get('role')}» را انتخاب کنید:",
                "gender": "👤 جنسیت خود را انتخاب کنید:",
                "age_range": "🎂 محدوده سنی خود را انتخاب کنید:",
                "province": "🏙️ استان خود را انتخاب کنید:",
                "phone": "📱 شماره تماس خود را از طریق دکمه زیر ارسال کنید:",
                "sample_type": "📎 نوع نمونه‌کار خود را انتخاب کنید:"
            }
            keyboards = {
                "role": make_keyboard(roles, per_row=2, include_back=False),
                "subrole": make_keyboard(subroles[state.get("role")]),
                "gender": make_keyboard(gender_options, per_row=1),
                "age_range": make_keyboard(age_ranges, per_row=2),
                "province": make_keyboard(provinces, per_row=4),
                "phone": phone_keyboard,
                "sample_type": make_keyboard(list(sample_types.keys()), per_row=2)
            }
            await message.reply(prompts[state["step"]], reply_markup=keyboards[state["step"]])
        return

    # 🎭 نقش
    if step == "role" and text in roles:
        state["role"] = text
        state["step"] = "subrole"
        await message.reply(f"🎯 یکی از ریزنقش‌های «{text}» را انتخاب کنید:",
                            reply_markup=make_keyboard(subroles[text]))
        user_states[chat_id] = state
        return

    # 🎯 ریزنقش
    if step == "subrole" and text in sum(subroles.values(), []):
        state["subrole"] = text
        state["step"] = "gender"
        await message.reply("👤 جنسیت خود را انتخاب کنید:", reply_markup=make_keyboard(gender_options, per_row=1))
        user_states[chat_id] = state
        return

    # 👤 جنسیت
    if step == "gender" and text in gender_options:
        state["gender"] = text
        state["step"] = "age_range"
        await message.reply("🎂 محدوده سنی خود را انتخاب کنید:", reply_markup=make_keyboard(age_ranges, per_row=2))
        user_states[chat_id] = state
        return

    # 🎂 سن
    if step == "age_range" and text in age_ranges:
        state["age_range"] = text
        state["step"] = "province"
        await message.reply("🏙️ استان خود را انتخاب کنید:", reply_markup=make_keyboard(provinces, per_row=4))
        user_states[chat_id] = state
        return

    # 🏙️ استان
    if step == "province" and text in provinces:
        state["province"] = text
        state["step"] = "phone"
        await message.reply("📱 شماره تماس خود را از طریق دکمه زیر ارسال کنید:", reply_markup=phone_keyboard)
        user_states[chat_id] = state
        return

    # 📞 شماره تماس
    if step == "phone":
        if hasattr(message, "contact") and message.contact:
            state["phone_number"] = message.contact.phone_number
            state["message_date"] = datetime.fromtimestamp(message.date.timestamp()).isoformat()
            state["step"] = "sample_type"
            await message.reply("📎 نوع نمونه‌کار خود را انتخاب کنید:",
                                reply_markup=make_keyboard(list(sample_types.keys()), per_row=2))
            user_states[chat_id] = state
        else:
            await message.reply("⚠️ لطفاً از دکمه ارسال شماره استفاده کنید:", reply_markup=phone_keyboard)
        return

    # 📎 نوع فایل
    if step == "sample_type" and text in sample_types:
        state["sample_type"] = text
        state["step"] = "file"
        await message.reply(f"{text}\n{sample_types[text]}\n\n📤 لطفاً فایل مربوطه را ارسال فرمایید:",
                            reply_markup=final_keyboard)
        user_states[chat_id] = state
        return

    # 📤 دریافت فایل و ثبت نهایی
    if step == "file" and hasattr(message, "document"):
        await message.reply("✅ فایل شما دریافت شد. در حال ثبت اطلاعات...")

        try:
            # ذخیره فایل
            filename = message.document.name or f"file_{message.document.id}"
            mime = message.document.mime_type or ""
            folder = {
                "video": "video", "image": "image", "text": "text",
                "application": "text", "audio": "audio"
            }.get(mime.split("/")[0], "other")

            path = os.path.join(UPLOAD_ROOT, folder, f"{chat_id}_{filename}")
            data = await client.download(message.document.id)

            with open(path, "wb") as f:
                f.write(data)

            # ذخیره اطلاعات در دیتابیس
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO submissions (
                    user_id, username, role, subrole, gender, age_range, province,
                    sample_type, file_path, file_size, phone_number, message_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user.id, username, state.get("role"), state.get("subrole"),
                state.get("gender"), state.get("age_range"), state.get("province"),
                state.get("sample_type"), path, file_size(path),
                state.get("phone_number"), state.get("message_date")
            ))

            conn.commit()
            record_id = cursor.fetchone()[0]
            print(f"New record added with ID: {record_id}")

        except Exception as e:
            print(f"Error saving data: {e}")
            await message.reply("⚠️ خطایی در ثبت اطلاعات رخ داد. لطفاً مجدداً تلاش کنید.")
            return
        finally:
            if conn:
                conn.close()

        user_states[chat_id] = {}

        await message.reply(
            "🙏 از اعتماد و همکاری شما سپاسگزاریم.\n"
            "📌 اطلاعات با موفقیت ثبت شد.\n"
            "برای ارسال مجدد، دکمه «شروع مجدد» را انتخاب فرمایید.",
            reply_markup=final_keyboard
        )
        return

    # پاسخ به پیام‌های نامربوط
    if step:
        await message.reply("⚠️ لطفاً از گزینه‌های ارائه شده استفاده کنید.")
    else:
        await message.reply("برای شروع دکمه «شروع» را انتخاب کنید.", reply_markup=start_keyboard)


# 🚀 اجرای ربات
if __name__ == "__main__":
    print("🚀 ربات با موفقیت اجرا شد و آماده دریافت اطلاعات کاربران محترم است...")
    try:
        bot.run()
    except KeyboardInterrupt:
        print("ربات متوقف شد")
    except Exception as e:
        print(f"خطا در اجرای ربات: {e}")