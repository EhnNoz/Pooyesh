import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import json
import re
from dotenv import load_dotenv
import os
from functools import wraps
import schedule  # اضافه کردن کتابخانه schedule

load_dotenv(dotenv_path=".env")
# تنظیمات API
BASE_API_URL = os.getenv("BASE_API_URL_TMP")
LOGIN_URL = f"{BASE_API_URL}/token/"
CHANNEL_API_URL = f"{BASE_API_URL}/rep/channel-code/?platform=1"
POSTS_API_URL = f"{BASE_API_URL}/rep/posts/"
GET_POSTS_API_URL = f"{BASE_API_URL}/rep/posts/?platform=1&channel={{id}}"

# اطلاعات ورود
USERNAME = os.getenv("API_USERNAME")
PASSWORD = os.getenv("API_PASSWORD")

# ذخیره توکن احراز هویت
access = None


def login():
    """ورود به سیستم و دریافت توکن دسترسی"""
    global access
    try:
        response = requests.post(LOGIN_URL, data={
            "username": USERNAME,
            "password": PASSWORD
        })
        response.raise_for_status()
        access = response.json().get("access")
        print("ورود موفقیت‌آمیز بود")
        return True
    except Exception as e:
        print(f"خطا در ورود: {e}")
        return False


def handle_auth_error(func):
    """دکوراتور برای مدیریت خطاهای احراز هویت"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        global access
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("توکن منقضی شده، در حال لاگین مجدد...")
                if login():
                    # تلاش مجدد پس از لاگین موفق
                    return func(*args, **kwargs)
                else:
                    raise Exception("لاگین مجدد ناموفق بود")
            else:
                raise

    return wrapper


@handle_auth_error
def get_channels():
    """دریافت لیست کانال‌ها"""
    headers = {"Authorization": f"Bearer {access}"}
    response = requests.get(CHANNEL_API_URL, headers=headers)
    response.raise_for_status()
    channels = response.json()
    print(f"{len(channels)} کانال یافت شد")
    return channels


@handle_auth_error
def get_last_post_date(channel_id):
    """دریافت تاریخ آخرین پست کانال"""
    headers = {"Authorization": f"Bearer {access}"}
    url = GET_POSTS_API_URL.format(id=channel_id)
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    posts = response.json()

    if posts and len(posts) > 0:
        # پیدا کردن جدیدترین پست بر اساس تاریخ
        latest_post = max(posts, key=lambda x: x.get('date', ''))
        return latest_post.get('date')
    else:
        # اگر پستی وجود ندارد، تاریخ امروز ساعت 00:00 برگردانده شود
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return today.isoformat()


def clean_channel_id(channel_id):
    """حذف @ از ابتدای شناسه کانال"""
    if channel_id and channel_id.startswith('@'):
        return channel_id[1:]
    return channel_id


def scrape_eitaa_channel(channel_name, since_date):
    """کرال کردن پست‌های یک کانال از تاریخ مشخص"""
    channel_name = clean_channel_id(channel_name)
    url = f"https://eitaa.com/{channel_name}"
    posts_data = []

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # پیدا کردن تمام پست‌ها
        post_wrappers = soup.select('div.etme_widget_message_wrap.js-widget_message_wrap')

        print(f"{len(post_wrappers)} پست در کانال {channel_name} پیدا شد")

        for post_wrapper in post_wrappers:
            # استخراج اطلاعات پست از المنت والد
            post_info = extract_post_info(post_wrapper, since_date)

            if post_info:
                # اگر تاریخ پست از since_date جدیدتر باشد
                if post_info['date'] > since_date:
                    posts_data.append(post_info)
                else:
                    # چون پست‌ها به ترتیب زمانی هستند، می‌توانیم وقتی به پست قدیمی رسیدیم متوقف شویم
                    break

        print(f"{len(posts_data)} پست جدید از کانال {channel_name} استخراج شد")
        return posts_data
    except Exception as e:
        print(f"خطا در کرال کانال {channel_name}: {e}")
        return []


def extract_post_info(post_wrapper, since_date):
    """استخراج اطلاعات از یک پست HTML"""
    try:
        # استخراج message_id
        message_id = post_wrapper.get('id')

        # بررسی وجود تاریخ
        time_element = post_wrapper.find('time', {'datetime': True})
        if not time_element:
            print(f"پست {message_id} فاقد تاریخ است، نادیده گرفته می‌شود")
            return None

        # استخراج و تبدیل تاریخ
        datetime_str = time_element.get('datetime')
        post_date = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))

        # تبدیل به زمان ایران (UTC+3:30)
        post_date_iran = post_date + timedelta(hours=0, minutes=00)

        # اگر تاریخ پست قدیمی‌تر از since_date است، پردازش نکن
        if post_date_iran <= since_date:
            return None

        # استخراج متن پست
        text_element = post_wrapper.select_one('.etme_widget_message_text.js-message_text')
        post_text = text_element.get_text(strip=True) if text_element else ""

        # استخراج هشتگ‌ها
        hashtags = extract_hashtags(post_text)

        # بررسی آیا پست فورواردی است و استخراج forward_from_chat_title
        forward_from_chat_title = ""
        is_forwarded = False

        forwarded_from_element = post_wrapper.select_one('.etme_widget_message_forwarded_from_name')
        if forwarded_from_element:
            is_forwarded = True
            forward_from_chat_title = forwarded_from_element.get_text(strip=True)

        # استخراج تعداد بازدیدها
        views_element = post_wrapper.select_one('.etme_widget_message_views[data-count]')
        if views_element and not is_forwarded:
            views = int(views_element.get('data-count', 0))
        else:
            views = 0

        # بررسی نوع رسانه
        document_mime_type = None

        # بررسی عکس
        if post_wrapper.select_one('.etme_widget_message_photo'):
            document_mime_type = 'image/jpeg'

        # بررسی ویدیو
        elif post_wrapper.select_one('.message_video_play.js-message_video_play'):
            document_mime_type = 'video/mp4'

        # بررسی صوت
        elif post_wrapper.select_one('.etme_widget_message_document_icon.accent_bg.audio'):
            document_mime_type = 'audio/mp3'

        return {
            'message_id': message_id,
            'post_text': post_text,
            'hashtags': ' '.join(hashtags),
            'date': post_date_iran,
            'collected_at': post_date_iran.strftime("%Y-%m-%d"),  # فقط تاریخ بدون ساعت
            'author': 1,  # همیشه 1
            'views': views,
            'is_forwarded': is_forwarded,
            'forward_from_chat_title': forward_from_chat_title,
            'document_mime_type': document_mime_type,
            'photo_file_id': message_id if document_mime_type == 'image/jpeg' else "",
            'video_file_id': message_id if document_mime_type == 'video/mp4' else "",
            'document_file_id': message_id if document_mime_type == 'audio/mp3' else ""
        }
    except Exception as e:
        print(f"خطا در استخراج اطلاعات پست: {e}")
        return None


def extract_hashtags(text):
    """استخراج هشتگ‌ها از متن"""
    return re.findall(r'#\w+', text)


def send_posts_to_api(posts):
    """ارسال پست‌ها به API با مدیریت خطای احراز هویت در سطح هر پست"""
    success_count = 0
    error_count = 0

    for post in posts:
        retry_count = 0
        max_retries = 2  # حداکثر 2 بار تلاش مجدد

        while retry_count <= max_retries:
            try:
                headers = {
                    "Authorization": f"Bearer {access}",
                    "Content-Type": "application/json"
                }

                # تبدیل تاریخ به فرمت ISO برای ارسال به API
                post_data = post.copy()
                post_data['date'] = post_data['date'].isoformat()

                # آماده کردن داده برای API
                api_data = {
                    'message_id': post_data['message_id'],
                    'post_text': post_data['post_text'],
                    'hashtags': post_data['hashtags'],
                    'date': post_data['date'],
                    'collected_at': post_data['collected_at'],
                    'author': 1,
                    'views': post_data['views'],
                    'forward_from_chat_title': post_data['forward_from_chat_title'],
                    'document_mime_type': post_data['document_mime_type'],
                    'photo_file_id': post_data['photo_file_id'],
                    'video_file_id': post_data['video_file_id'],
                    'document_file_id': post_data['document_file_id'],
                    'channel': post_data['channel']
                }

                # ارسال درخواست به API
                response = requests.post(POSTS_API_URL, headers=headers, json=api_data)
                response.raise_for_status()

                print(f"پست {post_data['message_id']} با موفقیت ارسال شد")
                success_count += 1
                break  # خروج از while در صورت موفقیت

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    print("توکن منقضی شده، در حال لاگین مجدد...")
                    if login():
                        retry_count += 1
                        print(f"تلاش {retry_count} برای ارسال مجدد پست {post.get('message_id', 'نامشخص')}")
                        continue  # تلاش مجدد با توکن جدید
                    else:
                        print("لاگین مجدد ناموفق بود")
                        error_count += 1
                        break
                else:
                    print(f"خطای HTTP {e.response.status_code} در ارسال پست {post.get('message_id', 'نامشخص')}: {e}")
                    error_count += 1
                    break

            except Exception as e:
                print(f"خطای غیرمنتظره در ارسال پست {post.get('message_id', 'نامشخص')}: {e}")
                error_count += 1
                break

            # تاخیر بین درخواست‌ها
            time.sleep(0.5)

    return success_count, error_count


def job():
    """تابع job برای اجرای برنامه اصلی"""
    print(f"شروع اجرای برنامه در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # ورود به سیستم
    if not login():
        return

    # دریافت کانال‌ها
    channels = get_channels()

    # محدود کردن به 5 کانال برای تست
    channels = channels[:]

    all_posts = []

    for channel in channels:
        channel_id = channel.get('channel_id')
        my_id = channel.get('id')
        print(f"پردازش کانال: {channel_id}")

        # دریافت تاریخ آخرین پست از API
        last_post_date_str = get_last_post_date(my_id)
        last_post_date = datetime.fromisoformat(last_post_date_str.replace('Z', '+00:00'))

        print(f"آخرین پست کانال در API: {last_post_date}")

        # کرال کردن کانال از تاریخ آخرین پست
        posts = scrape_eitaa_channel(channel_id, last_post_date)

        # اضافه کردن اطلاعات کانال به هر پست
        for post in posts:
            post['channel'] = my_id  # اینجا channel هست

        all_posts.extend(posts)

        # تاخیر بین درخواست‌ها
        time.sleep(1)

    # فقط پست‌های جدیدتر از آخرین پست API را ارسال کنیم
    if all_posts:
        df = pd.DataFrame(all_posts)

        # مرتب کردن بر اساس تاریخ
        df = df.sort_values('date', ascending=False)

        # تبدیل تاریخ به رشته برای نمایش
        df['date_str'] = df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # ذخیره در فایل اکسل
        # df.to_excel('eitaa_posts.xlsx', index=False)
        print(f"داده‌ها در فایل eitaa_posts.xlsx ذخیره شدند")

        # نمایش خلاصه‌ای از داده‌ها
        print(f"تعداد کل پست‌های استخراج شده: {len(df)}")
        print("۵ پست آخر:")
        print(df[['channel', 'date_str', 'author']].head().to_string(index=False))

        # ارسال پست‌ها به API
        print("\nارسال پست‌های جدید به API...")
        success_count, error_count = send_posts_to_api(all_posts)
        print(f"ارسال به API تکمیل شد: {success_count} موفق, {error_count} خطا")

    else:
        print("هیچ پست جدیدی یافت نشد")

    print(f"پایان اجرای برنامه در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)


def main():
    """تابع اصلی برای تنظیم زمان‌بندی"""
    print("برنامه زمان‌بندی شروع شد...")
    print("برنامه هر 30 دقیقه یکبار اجرا خواهد شد")
    print("برای توقف برنامه Ctrl+C را فشار دهید")

    # تنظیم زمان‌بندی برای اجرای هر 30 دقیقه
    schedule.every(30).minutes.do(job)

    # اجرای اولیه بلافاصله پس از شروع
    job()

    # حلقه بی‌نهایت برای اجرای زمان‌بندی
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nبرنامه توسط کاربر متوقف شد")