import os
import mimetypes
import pandas as pd
import psycopg2
import requests
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv
import random

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیمات دیتابیس
DB_CONFIG = {
    'host': '',
    'database': '',
    'user': '',
    'password': ''
}

# تنظیمات API بله
BALE_API_TOKEN = ''
BALE_BASE_URL = f'https://tapi.bale.ai/bot{BALE_API_TOKEN}/'

# مسیر فایل اکسل سردبیران
EDITORS_EXCEL_PATH = 'files/editor.xlsx'


class ContentSender:
    def __init__(self):
        self.session = requests.Session()

    def detect_content_type(self, file_path):
        """تشخیص نوع محتوا بر اساس پسوند فایل"""
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            return 'document'
        if mime_type.startswith('image/'):
            return 'photo'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        else:
            return 'document'

    def send_content(self, chat_id, content_path, caption=None):
        """ارسال محتوا بر اساس نوع آن"""
        # اگر content_path خالی باشد، فقط یک پیام متنی ارسال کنید
        if not content_path:
            return self.send_message(chat_id, caption or "اطلاعات ارسالی (بدون فایل)")

        content_type = self.detect_content_type(content_path)
        try:
            content_path = f'F:\sourcecode\Instaloader\{content_path}'
            with open(content_path, 'rb') as file:
                files = {content_type: file}
                print(chat_id)
                params = {'chat_id': chat_id}
                if caption:
                    params['caption'] = caption
                endpoint = {
                    'photo': 'sendPhoto',
                    'video': 'sendVideo',
                    'audio': 'sendAudio',
                    'document': 'sendDocument'
                }.get(content_type, 'sendDocument')
                url = f"{BALE_BASE_URL}{endpoint}"
                response = self.session.post(url, data=params, files=files)
                if response.status_code == 200:
                    return True
                else:
                    print(f"خطا در ارسال {content_type}: {response.text}")
                    return False
        except Exception as e:
            print(f"خطا در ارسال محتوا: {str(e)}")
            return False

    def send_message(self, chat_id, text):
        """ارسال یک پیام متنی"""
        try:
            params = {'chat_id': chat_id, 'text': text}
            url = f"{BALE_BASE_URL}sendMessage"
            response = self.session.post(url, data=params)
            if response.status_code == 200:
                return True
            else:
                print(f"خطا در ارسال پیام متنی: {response.text}")
                return False
        except Exception as e:
            print(f"خطا در ارسال پیام متنی: {str(e)}")
            return False


def update_editors_from_excel():
    """به‌روزرسانی جدول سردبیران از فایل اکسل بدون پاک کردن داده‌های قبلی"""
    conn = None
    try:
        df = pd.read_excel(EDITORS_EXCEL_PATH)
        print("ستون‌های فایل اکسل:", df.columns.tolist())
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        # ایجاد جدول اگر وجود نداشته باشد
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS editors (
                id SERIAL PRIMARY KEY,
                editor_id BIGINT,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                role VARCHAR(100) NOT NULL,
                subrole VARCHAR(100) DEFAULT '',
                count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # برای هر سطر در اکسل
        for _, row in df.iterrows():
            try:
                # تبدیل مقادیر خالی به مقادیر پیش‌فرض
                editor_id = int(row['آیدی']) if pd.notna(row['آیدی']) else None
                subrole = str(row['تخصص']) if pd.notna(row['تخصص']) else ""
                # بررسی وجود سردبیر با این مشخصات
                cursor.execute("""
                    SELECT id, count FROM editors 
                    WHERE editor_id = %s AND role = %s AND subrole = %s
                """, (editor_id, str(row['نقش']), subrole))
                existing_editor = cursor.fetchone()
                if existing_editor:
                    # اگر سردبیر وجود دارد، فقط اطلاعات پایه را آپدیت کن (count تغییر نمی‌کند)
                    cursor.execute("""
                        UPDATE editors 
                        SET first_name = %s, last_name = %s
                        WHERE id = %s
                    """, (
                        str(row['اسم']),
                        str(row['فامیل']),
                        existing_editor[0]
                    ))
                    print(f"سردبیر {row['اسم']} {row['فامیل']} آپدیت شد (count حفظ شد: {existing_editor[1]})")
                else:
                    # اگر سردبیر جدید است، آن را اضافه کن
                    cursor.execute("""
                        INSERT INTO editors (editor_id, first_name, last_name, role, subrole)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        editor_id,
                        str(row['اسم']),
                        str(row['فامیل']),
                        str(row['نقش']),
                        subrole
                    ))
                    print(f"سردبیر جدید {row['اسم']} {row['فامیل']} اضافه شد")
            except Exception as e:
                print(f"خطا در پردازش سردبیر {row['اسم']}: {str(e)}")
                continue
        conn.commit()
        print(f"به‌روزرسانی سردبیران با موفقیت انجام شد. تعداد: {len(df)}")
    except Exception as e:
        print(f"خطا در به‌روزرسانی سردبیران: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def find_available_editor(role, subrole=None):
    """یافتن سردبیر با ترکیب تصادفی و توازن بار"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = """
            SELECT id, editor_id, first_name, last_name, count
            FROM editors 
            WHERE role = %s AND editor_id IS NOT NULL
        """
        params = [role]
        if subrole:
            query += " AND subrole = %s"
            params.append(subrole)
        cursor.execute(query, params)
        editors = cursor.fetchall()
        if not editors:
            return None
        # انتخاب تصادفی با وزن معکوس تعداد اختصاصات (count)
        weights = [1 / (e[4] + 1) for e in editors]  # +1 برای جلوگیری از تقسیم بر صفر
        selected = random.choices(editors, weights=weights, k=1)[0]
        return selected[:4]  # حذف فیلد count از خروجی
    except Exception as e:
        print(f"خطا در یافتن سردبیر: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()


def update_document_editor(document_id, editor_db_id, editor_id):
    """به‌روزرسانی سند با سردبیر اختصاص یافته"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        # به‌روزرسانی سند با editor_id (نه id دیتابیس)
        cursor.execute("""
            UPDATE submissions 
            SET editor_id = %s
            WHERE id = %s
            RETURNING id
        """, (editor_id, document_id))
        if not cursor.fetchone():
            print(f"خطا: سند با شناسه {document_id} یافت نشد")
            conn.rollback()
            return False
        # افزایش تعداد اختصاص سردبیر
        cursor.execute("""
            UPDATE editors 
            SET count = count + 1
            WHERE id = %s
            RETURNING id
        """, (editor_db_id,))
        if not cursor.fetchone():
            print(f"خطا در افزایش تعداد اختصاص سردبیر {editor_db_id}")
            conn.rollback()
            return False
        conn.commit()
        print(f"سند {document_id} به سردبیر با شناسه {editor_id} اختصاص داده شد.")
        return True
    except psycopg2.Error as e:
        print(f"خطای دیتابیس در به‌روزرسانی: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def process_unassigned_contents():
    """پردازش محتواهای بدون سردبیر با در نظر گرفتن role و subrole"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        # تغییر: حذف شرط file_path IS NOT NULL برای ارسال رکوردهای بدون فایل نیز
        cursor.execute("""
            SELECT id, role, subrole, file_path, username, phone_number, social_link
            FROM submissions 
            WHERE editor_id IS NULL
        """)
        unassigned_contents = cursor.fetchall()
        if not unassigned_contents:
            print("هیچ محتوای بدون سردبیری یافت نشد.")
            return
        print(f"تعداد محتواهای بدون سردبیر: {len(unassigned_contents)}")
        sender = ContentSender()
        # تغییر: اضافه شدن social_link به حلقه
        for content_id, role, subrole, file_path, username, phone_number, social_link in unassigned_contents:
            # تبدیل subrole خالی به None
            subrole = subrole if subrole else None
            editor = find_available_editor(role, subrole)
            if editor:
                editor_db_id, editor_id, first_name, last_name = editor
                print(
                    f"ارسال محتوای {content_id} به سردبیر: {first_name} {last_name} (ID: {editor_id}, نقش: {role}, تخصص: {subrole or 'بدون تخصص'})")

                # تغییر: ساخت پیام با اطلاعات جدید شامل social_link
                sender_message_parts = [username, str(phone_number), role]
                if subrole:  # اضافه کردن subrole فقط اگر خالی نباشد
                    sender_message_parts.append(subrole)
                if social_link:  # اضافه کردن social_link فقط اگر خالی نباشد
                    sender_message_parts.append(social_link)

                sender_message = '\n'.join(sender_message_parts)

                # تغییر: ارسال محتوا - اگر file_path خالی باشد، send_content فقط پیام ارسال می‌کند
                if sender.send_content(editor_id, file_path, sender_message):
                    if update_document_editor(content_id, editor_db_id, editor_id):
                        print(f"محتوا {content_id} با موفقیت اختصاص داده شد.")
                    else:
                        print(f"خطا در به‌روزرسانی محتوای {content_id}")
                else:
                    print(f"خطا در ارسال محتوای {content_id} به سردبیر")
            else:
                print(f"سردبیر مناسبی برای محتوای {content_id} با نقش {role} و تخصص {subrole or 'بدون تخصص'} یافت نشد.")
    except Exception as e:
        print(f"خطا در پردازش محتواها: {str(e)}")
    finally:
        if conn:
            conn.close()


def nightly_job():
    """وظیفه شبانه"""
    print(f"شروع وظیفه شبانه در {datetime.now()}")
    update_editors_from_excel()
    process_unassigned_contents()
    print("وظیفه شبانه با موفقیت انجام شد.")


def hourly_job():
    """وظیفه ساعتی"""
    print(f"\n{'=' * 50}")
    print(f"شروع وظیفه ساعتی در {datetime.now()}")
    try:
        process_unassigned_contents()
        print("وظیفه ساعتی با موفقیت انجام شد.")
    except Exception as e:
        print(f"خطا در اجرای وظیفه ساعتی: {str(e)}")
    print(f"{'=' * 50}\n")


def main():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        # ایجاد جدول editors بدون محدودیت یکتایی
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS editors (
                id SERIAL PRIMARY KEY,
                editor_id BIGINT,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                role VARCHAR(100) NOT NULL,
                subrole VARCHAR(100) DEFAULT '',
                count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # ایجاد جدول submissions بدون ستون updated_at
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
                social_link TEXT,
                message_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                editor_id BIGINT
            );
        """)
        conn.commit()
    except Exception as e:
        print(f"خطا در ایجاد جداول: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    # اجرای اولیه
    print("برنامه در حال راه اندازی...")
    update_editors_from_excel()
    nightly_job()  # اجرای اولیه
    # تنظیم زمان‌بندی برای اجرای ساعتی
    schedule.every().minutes.do(hourly_job)
    # اجرای حلقه اصلی برنامه
    print("برنامه آماده است و هر ساعت محتواهای جدید را بررسی می‌کند...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # خواب یک دقیقه‌ای برای کاهش مصرف CPU


if __name__ == "__main__":
    main()