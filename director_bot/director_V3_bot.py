import os
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
        host="", # مثلاً "localhost" یا IP
        database="",
        user="",
        password="",
        port="5432" # پورت پیش‌فرض PostgreSQL
    )
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
            main_role TEXT,
            role TEXT,
            subrole TEXT,
            gender TEXT,
            age_range TEXT,
            province TEXT,
            sample_type TEXT,
            file_path TEXT,
            file_size TEXT,
            phone_number TEXT,
            social_link TEXT,
            message_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified BOOLEAN DEFAULT FALSE,
            verified_at TIMESTAMP,
            editor_id BIGINT,
            status TEXT DEFAULT 'pending'
        )
        """)
        conn.commit()
        print("✅ جدول submissions با موفقیت ایجاد یا تأیید شد.")
    except Exception as e:
        print(f"❌ خطا در ایجاد جدول: {e}")
    finally:
        if conn:
            conn.close()
# اجرای اولیه ساخت جدول
create_table()
# 🤖 راه‌اندازی ربات بله
TOKEN = "" # توکن ربات بله خود را اینجا وارد کنید
bot = Client(TOKEN)
user_states = {}
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
def set_start_message():
    text = (
        "🗂️ به بازوی پویش تولید محتوا خوش آمدید!\n"
        "هدف از این پویش، شناسایی کاربران نیمه حرفه‌ای در حوزه تولید محتواس.\n"
        "شما با انتخاب تخصص خود و ارسال نمونه کار می‌توانید به ما در این کار کمک کنید.\n"
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
link_keyboard = {
    "keyboard": [["ندارم"], ["↩️ بازگشت"], ["🔄 شروع مجدد"]],
    "resize_keyboard": True,
    "one_time_keyboard": True
}
confirm_keyboard = {
    "keyboard": [["✅ تایید میکنم"], ["✏️ ویرایش اطلاعات"], ["🔄 شروع مجدد"]],
    "resize_keyboard": True,
    "one_time_keyboard": True
}
# 🎭 نقش‌های اصلی
main_roles = [
    "منتشرکننده محتوا",
    "تولیدکننده محتوا"
]
# ⚠️ توضیحاتی که باید بعد از /start نمایش داده شود
start_message_descriptions = (
    "*📢 منتشرکننده محتوا:*\n"
    "افرادی که مسئولیت مدیریت و انتشار محتوا در کانال‌ها یا صفحات مختلف را بر عهده دارند. "
    "این افراد ممکن است خود تولیدکننده محتوا نباشند، اما در انتخاب و انتشار محتوای مناسب مهارت دارند.\n"
    "\n*🎨 تولیدکننده محتوا:*\n"
    "افرادی که به صورت حرفه‌ای یا نیمه‌حرفه‌ای در تولید انواع محتوا در فضای مجازی فعالیت می‌کنند. "
    "این محتوا می‌تواند در قالب‌های مختلفی مانند ویدیو، صوت، متن یا تصویر باشد."
)
# ⚠️ توضیحات جدید برای تولیدکننده محتوا
producer_main_description = (
    "*🎬 تولیدکننده ویدیوی کوتاه (ریل):*\n"
    "افرادی که ویدیوهای زیر یک دقیقه برای پلتفرم‌هایی مثل اینستاگرام یا یوتیوب شورتز می‌سازند. "
    "این محتواها معمولاً جذاب، سریع و پرمخاطب هستند.\n"
    "*🎵 تولیدکننده محتوای صوتی:*\n"
    "کسانی که محتوای شنیداری تولید می‌کنند.\n"
    "*🎤 بلاگر (راوی):*\n"
    "فردی که با روایت تجربه‌ها، روزمرگی‌ها یا موضوعات خاص (مثلاً سفر، سبک زندگی) محتوا تولید می‌کند.\n"
    "*🎨 گرافیست (ثابت و متحرک):*\n"
    "فردی که طراحی بصری انجام می‌دهد.\n"
    "*✏️ کاریکاتوریست:*\n"
    "طراح شخصیت یا موقعیت‌های طنزآمیز و اغراق‌شده برای نقد اجتماعی یا سرگرمی.\n"
    "*📷 عکاس:*\n"
    "فردی که تصاویر حرفه‌ای یا هنری تهیه می‌کند؛ شامل عکاسی پرتره، خبری، تبلیغاتی و مستند.\n"
    "*📊 کارشناس محتوا:*\n"
    "کسی که تحلیل و طراحی استراتژی برای محتوا انجام می‌دهد.\n"
    "*🎮 سازنده بازی:*\n"
    "طراح یا توسعه‌دهنده بازی‌های دیجیتال یا رومیزی، از ایده‌پردازی تا پیاده‌سازی فنی یا بصری.\n"
    "*📰 خبرنگار:*\n"
    "فردی که به جمع‌آوری و ارائه اخبار در حوزه‌های مختلف می‌پردازد.\n"
    "*✍️ نویسنده:*\n"
    "افرادی که انواع متون مکتوب را تولید می‌کنند.\n"
    "*🎮 تولیدکننده محتوا با هوش مصنوعی:*\n"
    "فردی که با ابزارهای مبتنی بر هوش مصنوعی محتوا تولید می‌کند؛ از تولید متن و تصویر تا ویدیو و صدا با کمک فناوری."
)
main_role_descriptions = {
    "منتشرکننده محتوا": (
        "*📢 منتشرکننده محتوا:*\n"
        "افرادی که مسئولیت مدیریت و انتشار محتوا در کانال‌ها یا صفحات مختلف را بر عهده دارند. "
        "این افراد ممکن است خود تولیدکننده محتوا نباشند، اما در انتخاب و انتشار محتوای مناسب مهارت دارند."
    ),
    "تولیدکننده محتوا": (
        "*🎨 تولیدکننده محتوا:*\n"
        "افرادی که به صورت حرفه‌ای یا نیمه‌حرفه‌ای در تولید انواع محتوا در فضای مجازی فعالیت می‌کنند. "
        "این محتوا می‌تواند در قالب‌های مختلفی مانند ویدیو، صوت، متن یا تصویر باشد."
    )
}
publisher_roles = [
    "ادمین و مالک کانال و صفحه",
    "ادمین کانال و صفحه"
]
producer_roles = {
    "تولیدکننده ویدیوی کوتاه (ریل)": [
        "استندآپ کمدی",
        "دابسمش",
        "تدوین آرشیوی",
        "فیلم و سریال کوتاه",
        "سایر"
    ],
    "تولیدکننده محتوای صوتی": [
        "پادکستر",
        "نریتور",
        "گوینده",
        "سایر"
    ],
    "بلاگر(راوی)": [],
    "گرافیست (ثابت و متحرک)": [
        "گرافیک ثابت",
        "موشن"
    ],
    "کاریکاتوریست": [],
    "عکاس": [],
    "کارشناس محتوا": [
        "تحلیل گر",
        "ایده‌پرداز",
        "سایر"
    ],
    "سازنده بازی": [],
    "خبرنگار": [
        "سیاسی",
        "اجتماعی",
        "فرهنگی",
        "علمی",
        "فن‌آوری",
        "سایر"
    ],
    "نویسنده": [
        "مینیمال‌نویس",
        "مقاله",
        "داستان کوتاه",
        "فیلمنامه کوتاه",
        "طنز",
        "تحلیل",
        "یادداشت",
        "سناریونویس"
    ],
    "تولیدکننده محتوا با هوش مصنوعی": []
}
producer_role_descriptions = {
    "تولیدکننده ویدیوی کوتاه (ریل)": (
        "*🎬 تولیدکننده ویدیوی کوتاه (ریل):*\n"
        "افرادی که ویدیوهای زیر یک دقیقه برای پلتفرم‌هایی مثل اینستاگرام یا یوتیوب شورتز می‌سازند. "
        "این محتواها معمولاً جذاب، سریع و پرمخاطب هستند.\n"
        "*🌿حوزه ها:*\n"
        "▫️ استندآپ کمدی: خلق و اجرای ویدیوهای کوتاه طنز در قالب استندآپ، با هدف سرگرم کردن مخاطب.\n"
        "▫️ دابسمش: بازسازی ویدیوها با لب‌خوانی بر روی صداهای معروف یا دیالوگ‌های فیلم‌ها به‌صورت طنزآمیز.\n"
        "▫️ تدوین آرشیوی: استفاده از کلیپ‌ها و ویدیوهای آماده و قدیمی برای تدوین و خلق محتوای جدید.\n"
        "▫️ فیلم و سریال کوتاه: تولید محتوای داستانی با زمان کوتاه، معمولاً زیر ۵ دقیقه، با ساختار سینمایی یا اپیزودیک."
    ),
    "تولیدکننده محتوای صوتی": (
        "*🎵 تولیدکننده محتوای صوتی:*\n"
        "کسانی که محتوای شنیداری تولید می‌کنند.\n"
        "*🌿حوزه ها:*\n"
        "▫️ پادکستر: سازنده برنامه‌های صوتی با موضوعات مختلف مانند مصاحبه، آموزش یا روایت.\n"
        "▫️ نریتور: فردی که داستان یا متن را با صدای خود روایت می‌کند، گاهی برای کتاب‌های صوتی یا مستندها.\n"
        "▫️ گوینده: فردی که متون را با فن بیان مناسب برای رادیو، تیزر، تبلیغات یا کتاب‌ صوتی می‌خواند."
    ),
    "بلاگر(راوی)": (
        "*🎤 بلاگر (راوی):*\n"
        "فردی که با روایت تجربه‌ها، روزمرگی‌ها یا موضوعات خاص (مثلاً سفر، سبک زندگی) محتوا تولید می‌کند."
    ),
    "گرافیست (ثابت و متحرک)": (
        "*🎨 گرافیست (ثابت و متحرک):*\n"
        "فردی که طراحی بصری انجام می‌دهد.\n"
        "انواع:\n"
        "▫️ گرافیک ثابت: طراحی پوستر، پست، بنر یا اینفوگرافی بدون حرکت.\n"
        "▫️ موشن: طراحی گرافیکی متحرک برای ویدیوها یا تیزرها"
    ),
    "کاریکاتوریست": (
        "*✏️ کاریکاتوریست:*\n"
        "طراح شخصیت یا موقعیت‌های طنزآمیز و اغراق‌شده برای نقد اجتماعی یا سرگرمی."
    ),
    "عکاس": (
        "*📷 عکاس:*\n"
        "فردی که تصاویر حرفه‌ای یا هنری تهیه می‌کند؛ شامل عکاسی پرتره، خبری، تبلیغاتی و مستند."
    ),
    "کارشناس محتوا": (
        "*📊 کارشناس محتوا:*\n"
        "کسی که تحلیل و طراحی استراتژی برای محتوا انجام می‌دهد.\n"
        "*🌿حوزه ها:*\n"
        "▫️ تحلیل‌گر: بررسی عملکرد محتوا، نیاز مخاطب و روندهای بازار برای بهینه‌سازی تولید.\n"
        "▫️ ایده‌پرداز: خلق ایده‌های نوآورانه برای انواع محتوا بر اساس اهداف برند یا رسانه."
    ),
    "سازنده بازی": (
        "*🎮 سازنده بازی:*\n"
        "طراح یا توسعه‌دهنده بازی‌های دیجیتال یا رومیزی، از ایده‌پردازی تا پیاده‌سازی فنی یا بصری."
    ),
    "خبرنگار": (
        "*📰 خبرنگار:*\n"
        "فردی که به جمع‌آوری و ارائه اخبار در حوزه‌های مختلف می‌پردازد.\n"
        "*🌿حوزه ها:*\n"
        "▫️ سیاسی: پوشش اخبار و رویدادهای سیاسی.\n"
        "▫️ اجتماعی: تمرکز بر مسائل اجتماعی، شهری، رفاه عمومی و جامعه.\n"
        "▫️ فرهنگی: پرداختن به موضوعات فرهنگ، هنر، ادبیات و رویدادهای هنری.\n"
        "▫️ علمی: گزارش و تحلیل تحولات علمی و پژوهشی.\n"
        "▫️ فناوری: پوشش اخبار فناوری، استارتاپ‌ها، نوآوری و تکنولوژی‌های نوین."
    ),
    "نویسنده": (
        "*✍️ نویسنده:*\n"
        "افرادی که انواع متون مکتوب را تولید می‌کنند.\n"
        "*🌿حوزه ها:*\n"
        "▫️ مینیمال‌نویس: خلق متن‌های بسیار کوتاه، ولی معنا‌دار با بار احساسی یا مفهومی.\n"
        "▫️ سناریو‌نویس: خلق سناریوهای کوتاه و جذاب برای تولید محتوا\n"
        "▫️ مقاله: نویسنده مقاله‌های تحلیلی یا آموزشی در قالب رسمی و ساختار یافته.\n"
        "▫️ داستان کوتاه: تولید داستان‌های کوتاه ، داستانک یا رمان.\n"
        "▫️ فیلمنامه کوتاه: نگارش متن برای فیلم یا سریال کوتاه با ساختار نمایشی.\n"
        "▫️ طنز: نوشتن محتوای طنز، کنایه‌آمیز یا انتقادی با لحن شوخ‌طبعانه.\n"
        "▫️ تحلیل: ارائه تحلیل پیرامون موضوعات فرهنگی، سیاسی، اجتماعی و ...\n"
        "▫️ یادداشت: نوشته‌های کوتاه شخصی یا تخصصی با لحن غیررسمی و روان."
    ),
    "تولیدکننده محتوا با هوش مصنوعی": (
        "*🎮 تولیدکننده محتوا با هوش مصنوعی:*\n"
        "فردی که با ابزارهای مبتنی بر هوش مصنوعی محتوا تولید می‌کند؛ از تولید متن و تصویر تا ویدیو و صدا با کمک فناوری."
    )
}
gender_options = ["زن", "مرد"]
age_ranges = [
    "تا ۱۸ سال", "۱۸ تا ۲۵ سال", "۲۶ تا ۳۵ سال",
    "۳۶ تا ۴۵ سال", "۴۶ تا ۶۰ سال", "بیشتر از ۶۰ سال"
]
provinces = [
    "آذربایجان شرقی", "آذربایجان غربی", "اردبیل", "اصفهان", "البرز", "ایلام", "بوشهر", "تهران",
    "چهارمحال و بختیاری", "خراسان جنوبی", "خراسان رضوی", "خراسان شمالی", "خوزستان", "زنجان",
    "سمنان", "سیستان و بلوچستان", "فارس", "قزوین", "قم", "کردستان", "کرمان", "کرمانشاه",
    "کهگیلویه و بویراحمد", "گلستان", "گیلان", "لرستان", "مازندران", "مرکزی", "هرمزگان", "همدان", "یزد"
]
sample_types = {
    "فایل ویدیویی 🎬": "MP4, MOV, MKV, AVI",
    "فایل صوتی 🎵": "MP3, WAV, AAC, OGG",
    "فایل تصویری 🖼️": "JPG, PNG",
    "فایل متنی 📄": "PDF, DOCX"
}
def file_size(path):
    try:
        size_kb = round(os.path.getsize(path) / 1024)
        return f"{size_kb} KB" if size_kb < 1024 else f"{round(size_kb / 1024, 1)} MB"
    except:
        return "نامشخص"
def get_summary_text(state):
    main_role = state.get("main_role", "تعیین نشده")
    role = state.get("role", "تعیین نشده")
    subrole = state.get("subrole", "-")
    gender = state.get("gender", "تعیین نشده")
    age_range = state.get("age_range", "تعیین نشده")
    province = state.get("province", "تعیین نشده")
    phone = state.get("phone_number", "تعیین نشده")
    social = state.get("social_link", "ندارم")
    sample_type = state.get("sample_type", "-")
    file_info = ""
    if "file_path" in state:
        file_info = f"▪️ حجم نمونه کار: {state.get('file_size', 'نامشخص')}\n"
    text = (
        "📝 خلاصه اطلاعات وارد شده:\n"
        f"▪️ نقش اصلی: {main_role}\n"
        f"▪️ تخصص: {role}\n"
        f"▪️ حوزه تخصص: {subrole}\n"
        f"▪️ جنسیت: {gender}\n"
        f"▪️ محدوده سنی: {age_range}\n"
        f"▪️ استان: {province}\n"
        f"▪️ شماره تماس: {phone}\n"
        f"▪️ لینک شبکه اجتماعی: {social}\n"
    )
    if sample_type != "-":
        text += f"▪️ نوع نمونه کار: {sample_type}\n"
    if file_info:
        text += file_info
    text += "\nلطفاً صحت اطلاعات را تأیید کنید:"
    return text
async def show_confirmation(message, state):
    state["step"] = "confirmation"
    user_states[message.chat.id] = state
    await message.reply(
        get_summary_text(state),
        reply_markup=confirm_keyboard
    )
async def save_file(message, file_type="sample"):
    try:
        filename = message.document.name or f"{file_type}_{message.document.id}"
        folder = {
            "video": "video", "image": "image", "text": "text",
            "application": "text", "audio": "audio"
        }.get(message.document.mime_type.split("/")[0], "other")
        path = os.path.join(UPLOAD_ROOT, folder, f"{message.chat.id}_{filename}")
        data = await message.client.download(message.document.id)
        with open(path, "wb") as f:
            f.write(data)
        return path, file_size(path)
    except Exception as e:
        print(f"Error saving {file_type}: {e}")
        return None, None

@bot.on_message()
async def handle_message(client, message):
    chat_id = message.chat.id
    user = message.author
    username = user.username or user.full_name or str(user.id)
    text = (message.text or "").strip()
    state = user_states.get(chat_id, {})
    step = state.get("step")

    if text in ["/start", "شروع", "🔄 شروع مجدد"]:
        # ارسال توضیحات مورد نظر بعد از start
        await message.reply(start_message_descriptions)
        user_states[chat_id] = {"step": "main_role"}
        await message.reply(
            "🎯 فعالیت تخصصی شما در چه زمینه‌ای است؟",
            reply_markup=make_keyboard(main_roles, per_row=2)
        )
        return

    if text == "↩️ بازگشت":
        main_role = state.get("main_role")
        role = state.get("role")
        current_step = step
        if current_step == "confirmation":
            if "file_path" in state:
                prev_step = "file"
            else:
                prev_step = "social_link"
        elif current_step == "file":
            prev_step = "sample_type"
        elif current_step == "sample_type":
            prev_step = "social_link"
        elif current_step == "social_link":
            prev_step = "phone"
        elif current_step == "phone":
            prev_step = "province"
        elif current_step == "province":
            prev_step = "age_range"
        elif current_step == "age_range":
            prev_step = "gender"
        elif current_step == "gender":
            if main_role == "تولیدکننده محتوا" and role in producer_roles and len(producer_roles[role]) > 0:
                prev_step = "subrole"
            else:
                prev_step = "role"
        elif current_step == "subrole":
            prev_step = "role"
        elif current_step == "role":
            prev_step = "main_role"
        elif current_step == "main_role":
            prev_step = None
        else:
            prev_step = None

        if prev_step:
            state["step"] = prev_step
            user_states[chat_id] = state
            if state["step"] == "main_role":
                await message.reply("🎯 فعالیت تخصصی شما در چه زمینه‌ای است؟",
                                    reply_markup=make_keyboard(main_roles, per_row=2))
            elif state["step"] == "role":
                if main_role == "منتشرکننده محتوا":
                    await message.reply("✨ کدام گزینه تخصص شما را بهتر توصیف می‌کند؟",
                                        reply_markup=make_keyboard(publisher_roles))
                else:
                    await message.reply("✨ کدام گزینه تخصص شما را بهتر توصیف می‌کند؟",
                                        reply_markup=make_keyboard(list(producer_roles.keys())))
            elif state["step"] == "subrole":
                await message.reply(f"✨ لطفا حوزه‌ی تخصص خود را انتخاب کنید؟",
                                    reply_markup=make_keyboard(producer_roles[role]))
            elif state["step"] == "gender":
                await message.reply("👤 جنسیت خود را انتخاب کنید:",
                                    reply_markup=make_keyboard(gender_options, per_row=1))
            elif state["step"] == "age_range":
                await message.reply("🎂 محدوده سنی خود را انتخاب کنید:",
                                    reply_markup=make_keyboard(age_ranges, per_row=2))
            elif state["step"] == "province":
                await message.reply("🏙️ استان خود را انتخاب کنید:",
                                    reply_markup=make_keyboard(provinces, per_row=4))
            elif state["step"] == "phone":
                await message.reply("📱 شماره تماس خود را از طریق دکمه زیر ارسال کنید:",
                                    reply_markup=phone_keyboard)
            elif state["step"] == "social_link":
                await message.reply(
                    "🌐 لطفاً آدرس شبکه اجتماعی خود را ارسال کنید:\n"
                    "مثال: https://ble.ir/Ad_iraneman\n"
                    "اگر ندارید، گزینه 'ندارم' را انتخاب کنید.",
                    reply_markup=link_keyboard
                )
            elif state["step"] == "sample_type":
                await message.reply("📎 نوع نمونه‌کار خود را انتخاب کنید:",
                                    reply_markup=make_keyboard(list(sample_types.keys()), per_row=2))
            elif state["step"] == "file":
                await message.reply(
                    f"{state.get('sample_type')}\n{sample_types[state.get('sample_type')]}\n📤 لطفاً فایل مربوطه را ارسال فرمایید:",
                    reply_markup=final_keyboard # یا کیبورد مناسب‌تری
                )
        return

    # 🎭 نقش اصلی
    if step == "main_role" and text in main_roles:
        state["main_role"] = text
        state["step"] = "role"
        # Send description for main role
        if text == "تولیدکننده محتوا":
             # ارسال توضیحات جدید برای تولیدکننده محتوا
            await message.reply(producer_main_description)
        else:
            # ارسال توضیحات عادی برای منتشرکننده
            await message.reply(main_role_descriptions[text])
        if text == "منتشرکننده محتوا":
            await message.reply("✨ کدام گزینه تخصص شما را بهتر توصیف می‌کند؟",
                                reply_markup=make_keyboard(publisher_roles))
        else:
            await message.reply("✨ کدام گزینه تخصص شما را بهتر توصیف می‌کند؟",
                                reply_markup=make_keyboard(list(producer_roles.keys())))
        user_states[chat_id] = state
        return

    # 🎯 نقش منتشرکنندگان
    if step == "role" and state.get("main_role") == "منتشرکننده محتوا" and text in publisher_roles:
        state["role"] = text
        state["step"] = "gender"
        await message.reply("👤 جنسیت خود را انتخاب کنید:", reply_markup=make_keyboard(gender_options, per_row=1))
        user_states[chat_id] = state
        return

    # 🎯 نقش تولیدکنندگان
    if step == "role" and state.get("main_role") == "تولیدکننده محتوا" and text in producer_roles:
        state["role"] = text
        # Send detailed description for producer role
        await message.reply(producer_role_descriptions[text])
        if text in producer_roles and len(producer_roles[text]) > 0:
            state["step"] = "subrole"
            await message.reply(f"✨ لطفا حوزه‌ی تخصص خود را انتخاب کنید؟",
                                reply_markup=make_keyboard(producer_roles[text]))
        else:
            state["step"] = "gender"
            await message.reply("👤 جنسیت خود را انتخاب کنید:", reply_markup=make_keyboard(gender_options, per_row=1))
        user_states[chat_id] = state
        return

    # 🎯 زیرنقش تولیدکنندگان
    if step == "subrole" and state.get("main_role") == "تولیدکننده محتوا" and text in sum(producer_roles.values(), []):
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
            state["step"] = "social_link"
            await message.reply(
                "🌐 لطفاً آدرس شبکه اجتماعی خود را ارسال کنید:\n"
                "مثال: https://ble.ir/Ad_iraneman\n"
                "اگر ندارید، گزینه 'ندارم' را انتخاب کنید.",
                reply_markup=link_keyboard
            )
            user_states[chat_id] = state
        else:
            await message.reply("⚠️ لطفاً از دکمه ارسال شماره استفاده کنید:", reply_markup=phone_keyboard)
        return

    # 🌐 دریافت آدرس شبکه اجتماعی
    if step == "social_link":
        if text == "ندارم":
            state["social_link"] = "ندارم"
            if state.get("main_role") == "تولیدکننده محتوا":
                state["step"] = "sample_type"
                await message.reply("📎 نوع نمونه‌کار خود را انتخاب کنید:",
                                    reply_markup=make_keyboard(list(sample_types.keys()), per_row=2))
            else:
                await show_confirmation(message, state)
        elif text and (text.startswith("http") or text.startswith("@")):
            if len(text) > 250:
                await message.reply(
                    "⚠️ طول لینک ارسالی زیاد است.\n"
                    "لطفاً لینک کوتاه‌تر یا معتبر ارسال کنید:",
                    reply_markup=link_keyboard
                )
                return
            state["social_link"] = text
            if state.get("main_role") == "تولیدکننده محتوا":
                state["step"] = "sample_type"
                await message.reply("📎 نوع نمونه‌کار خود را انتخاب کنید:",
                                    reply_markup=make_keyboard(list(sample_types.keys()), per_row=2))
            else:
                await show_confirmation(message, state)
        else:
            await message.reply(
                "⚠️ لطفاً آدرس معتبر وارد کنید یا گزینه 'ندارم' را انتخاب کنید:\n"
                "(مثال: https://ble.ir/Ad_iraneman)",
                reply_markup=link_keyboard
            )
        user_states[chat_id] = state
        return

    # 📎 نوع فایل (فقط برای تولیدکنندگان)
    if step == "sample_type" and text in sample_types and state.get("main_role") == "تولیدکننده محتوا":
        state["sample_type"] = text
        state["step"] = "file"
        # ساخت کیبورد سفارشی برای این مرحله که شامل دکمه بازگشت هم باشد
        custom_file_keyboard = {
            "keyboard": [
                ["↩️ بازگشت"],
                ["🔄 شروع مجدد"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        await message.reply(
            f"{text}\n"
            f" {sample_types[text]}\n"
            "📤 لطفاً فایل مربوطه را ارسال فرمایید:",
        reply_markup = custom_file_keyboard
        )
        user_states[chat_id] = state
        return

    # 📤 دریافت فایل (فقط برای تولیدکنندگان)
    if step == "file" and hasattr(message, "document") and state.get("main_role") == "تولیدکننده محتوا":
        path, size = await save_file(message)
        if path:
            state["file_path"] = path
            state["file_size"] = size
            await show_confirmation(message, state)
        else:
            # ساخت کیبورد سفارشی برای این مرحله در صورت خطا
            custom_error_keyboard = {
                "keyboard": [
                    ["⚠️ خطایی در دریافت فایل رخ داد. لطفاً مجدداً تلاش کنید."],
                    ["↩️ بازگشت"],
                    ["🔄 شروع مجدد"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True
            }
            await message.reply("⚠️ خطایی در دریافت فایل رخ داد. لطفاً مجدداً تلاش کنید.", reply_markup=custom_error_keyboard) # استفاده از کیبورد سفارشی
        return

    # ✅ تأیید نهایی اطلاعات
    if step == "confirmation":
        if text == "✅ تایید میکنم":
            # ذخیره‌سازی فعال شده است
            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # آماده‌سازی داده‌ها برای درج
                insert_data = {
                    'user_id': user.id,
                    'username': username,
                    'main_role': state.get("main_role"),
                    'role': state.get("role"),
                    'subrole': state.get("subrole", ''), # اگر نباشد، رشته خالی
                    'gender': state.get("gender"),
                    'age_range': state.get("age_range"),
                    'province': state.get("province"),
                    'sample_type': state.get("sample_type", ''), # اگر نباشد، رشته خالی
                    'file_path': state.get("file_path", ''), # اگر نباشد، رشته خالی
                    'file_size': state.get("file_size", ''), # اگر نباشد، رشته خالی
                    'phone_number': state.get("phone_number"),
                    'social_link': state.get("social_link"),
                    'message_date': state.get("message_date") # این باید یک datetime باشد
                }

                # اجرای دستور INSERT
                insert_query = sql.SQL("""
                    INSERT INTO submissions (
                        user_id, username, main_role, role, subrole,
                        gender, age_range, province, sample_type,
                        file_path, file_size, phone_number, social_link, message_date
                    ) VALUES (
                        %(user_id)s, %(username)s, %(main_role)s, %(role)s, %(subrole)s,
                        %(gender)s, %(age_range)s, %(province)s, %(sample_type)s,
                        %(file_path)s, %(file_size)s, %(phone_number)s, %(social_link)s, %(message_date)s
                    )
                """)
                cursor.execute(insert_query, insert_data)
                conn.commit()
                print(f"✅ اطلاعات کاربر {user.id} با موفقیت در دیتابیس ذخیره شد.")

            except Exception as e:
                print(f"❌ خطا در ذخیره‌سازی داده‌ها برای کاربر {user.id}: {e}")
                if conn:
                    conn.rollback() # در صورت خطا، تغییرات را برگردان
                # می‌توانید پیام خطا به کاربر هم ارسال کنید
                await message.reply(f"❌ متاسفانه خطایی در ذخیره اطلاعات رخ داد: {str(e)}")
                # در صورت خطا، فرآیند را متوقف نکنید تا کاربر بتواند دوباره تلاش کند یا شروع مجدد کند
                # بنابراین وضعیت را پاک نمی‌کنیم و ادامه می‌دهیم
                return # از ادامه اجرای این تابع جلوگیری می‌کند تا پیام تکمیل نادرست ارسال نشود
            finally:
                if conn:
                    cursor.close()
                    conn.close()

            # تنظیم وضعیت به "تکمیل شده" به جای پاک کردن کامل
            user_states[message.chat.id] = {"step": "completed"} # یا user_states[message.chat.id]["step"] = "completed"
            # user_states[message.chat.id] = {} # این خط را کامنت یا حذف کنید

            await message.reply(
                "🙏 از اعتماد و همکاری شما سپاسگزاریم.\n"
                "📌 اطلاعات با موفقیت ثبت و تایید شد.\n"
                "📌 اگر در حوزه دیگری هم تخصص دارید دکمه «شروع مجدد» را انتخاب کنید.\n"
                "✅ برای عضویت در گروه عمومی نهضت تولید و انتشار محتوا و اطلاع از آخرین اخبار و اطلاعات در این حوزه لطفا روی لینک زیر کلیک کنید.\n"
                "@Ad_iraneman",
                reply_markup=final_keyboard
            )
        elif text == "✏️ ویرایش اطلاعات":
            user_states[chat_id] = {"step": "main_role"}
            await message.reply("🎯 فعالیت تخصصی شما در چه زمینه‌ای است؟",
                                reply_markup=make_keyboard(main_roles, per_row=2))
        elif text == "🔄 شروع مجدد":
            user_states[chat_id] = {"step": "main_role"}
            await message.reply("🎯 فعالیت تخصصی شما در چه زمینه‌ای است؟",
                                reply_markup=make_keyboard(main_roles, per_row=2))
        else:
            await message.reply("لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                                reply_markup=confirm_keyboard)
        return # این return مهم است تا ادامه کد اجرا نشود

    # پاسخ به پیام‌های نامربوط
    # اضافه کردن شرط برای وضعیت "completed"
    if step and step != "completed": # فقط اگر مرحله تعریف شده باشد و تکمیل نشده باشد
        await message.reply("⚠️ لطفاً از گزینه‌های ارائه شده استفاده کنید.")
    elif step == "completed":
        # اگر کاربر پس از تکمیل، پیام دیگری ارسال کند، می‌توانید یک پیام مناسب ارسال کنید
        # یا هیچ پیامی ارسال نکنید. در اینجا یک پیام ساده ارسال می‌کنیم
         await message.reply("✅ فرآیند شما تکمیل شد. برای شروع مجدد، دکمه «شروع مجدد» را بزنید.", reply_markup=final_keyboard)
    else: # step is None or not handled
        # اینجا فقط در صورتی اجرا می‌شود که کاربر پیامی غیر از /start یا شروع ارسال کند و وضعیتی نداشته باشد
        # اما چون کاربر تازه تایید کرده و وضعیت "completed" دارد، این شرط اجرا نمی‌شود.
        # اما برای امنیت بیشتر، می‌توانیم آن را نگه داریم.
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
