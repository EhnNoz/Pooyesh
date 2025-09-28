import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
from dotenv import load_dotenv
import os
import re
import jdatetime  # افزودن کتابخانه تبدیل تاریخ
import schedule  # افزودن کتابخانه زمان‌بندی

load_dotenv(dotenv_path=".env")
# تنظیمات API
BASE_API_URL = os.getenv("BASE_API_URL_TMP")

LOGIN_URL = f"{BASE_API_URL}/token/"
CHANNEL_API_URL = f"{BASE_API_URL}/rep/channel-code/?platform=2"
POSTS_API_URL = f"{BASE_API_URL}/rep/posts/"
POSTS_CREATE_API_URL = f"{BASE_API_URL}/rep/posts/"

# اطلاعات لاگین (لطفا اطلاعات واقعی را جایگزین کنید)
LOGIN_CREDENTIALS = {
    "username": os.getenv("API_USERNAME"),
    "password": os.getenv("API_PASSWORD")
}

# متغیرهای سراسری برای مدیریت توکن
access_token = None
token_expiry = None

# دیکشنری برای تبدیل نام ماه‌های فارسی به انگلیسی
PERSIAN_MONTHS = {
    'فروردین': 1,
    'اردیبهشت': 2,
    'خرداد': 3,
    'تیر': 4,
    'مرداد': 5,
    'شهریور': 6,
    'مهر': 7,
    'آبان': 8,
    'آذر': 9,
    'دی': 10,
    'بهمن': 11,
    'اسفند': 12
}

# دیکشنری برای تبدیل اعداد فارسی به انگلیسی
PERSIAN_TO_ENGLISH_NUMBERS = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
}


def convert_persian_numbers(text):
    """تبدیل اعداد فارسی به انگلیسی"""
    if not text:
        return ""
    for persian, english in PERSIAN_TO_ENGLISH_NUMBERS.items():
        text = text.replace(persian, english)
    return text


def parse_persian_date(date_str):
    """تبدیل تاریخ شمسی به میلادی"""
    if not date_str or not date_str.strip():
        return None

    date_str = convert_persian_numbers(date_str.strip())

    # الگوهای مختلف تاریخ
    patterns = [
        # الگو: ۱۴ اردیبهشت ۱۳۹۷
        r'(\d{1,2})\s+(\S+)\s+(\d{4})',
        # الگو: ۲ شهریور (بدون سال)
        r'(\d{1,2})\s+(\S+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            if len(match.groups()) == 3:  # با سال
                day = int(match.group(1))
                month_name = match.group(2)
                year = int(match.group(3))
            else:  # بدون سال
                day = int(match.group(1))
                month_name = match.group(2)
                year = jdatetime.datetime.now().year  # سال جاری

            # تبدیل نام ماه به عدد
            month = PERSIAN_MONTHS.get(month_name)
            if not month:
                continue

            try:
                # ایجاد تاریخ شمسی و تبدیل به میلادی
                persian_date = jdatetime.date(year, month, day)
                gregorian_date = persian_date.togregorian()
                return gregorian_date
            except ValueError:
                continue

    return None


# تابع برای دریافت توکن با قابلیت تمدید
def get_access_token_with_retry():
    global access_token, token_expiry

    # اگر توکن معتبر داریم، از آن استفاده می‌کنیم
    if access_token and token_expiry and token_expiry > datetime.now():
        return access_token

    # در غیر این صورت توکن جدید دریافت می‌کنیم
    try:
        response = requests.post(LOGIN_URL, data=LOGIN_CREDENTIALS)
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get("access")

        # محاسبه زمان انقضای توکن (فرض می‌کنیم ۱ ساعت معتبر است)
        token_expiry = datetime.now() + timedelta(hours=1)

        return access_token
    except requests.exceptions.RequestException as e:
        print(f"خطا در دریافت توکن: {e}")
        return None


# تابع برای دریافت لیست کانال‌ها با مدیریت توکن منقضی شده
def get_channels_with_retry():
    max_retries = 2
    for attempt in range(max_retries):
        token = get_access_token_with_retry()
        if not token:
            return []

        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(CHANNEL_API_URL, headers=headers)

            # اگر توکن منقضی شده باشد
            if response.status_code == 401 and attempt == 0:
                print("توکن منقضی شده، در حال دریافت توکن جدید...")
                global access_token, token_expiry
                access_token = None
                token_expiry = None
                continue

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"خطا در دریافت کانال‌ها: {e}")
            return []

    return []


# تابع برای دریافت پست‌های یک کانال با مدیریت توکن منقضی شده
def get_posts_with_retry(channel_id):
    max_retries = 2
    for attempt in range(max_retries):
        token = get_access_token_with_retry()
        if not token:
            return []

        headers = {"Authorization": f"Bearer {token}"}
        url = f"{POSTS_API_URL}?platform=2&channel={channel_id}"
        try:
            response = requests.get(url, headers=headers)

            # اگر توکن منقضی شده باشد
            if response.status_code == 401 and attempt == 0:
                print("توکن منقضی شده، در حال دریافت توکن جدید...")
                global access_token, token_expiry
                access_token = None
                token_expiry = None
                continue

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"خطا در دریافت پست‌های کانال {channel_id}: {e}")
            return []

    return []


# تابع برای ارسال پست‌ها به API
def send_posts_to_api(posts_data):
    if not posts_data:
        print("هیچ داده‌ای برای ارسال وجود ندارد.")
        return False

    token = get_access_token_with_retry()
    if not token:
        print("توکن معتبری برای ارسال داده وجود ندارد.")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    success_count = 0
    error_count = 0

    for post in posts_data:
        try:
            # ایجاد داده‌های مورد نیاز برای API
            api_data = {
                "channel": post["channel"],
                "post_id": post["post_id"],
                "message_id": post["message_id"],
                "post_text": post["post_text"],
                "hashtags": post["hashtags"],
                "date": post["date"],
                "collected_at": post["collected_at"],
                "author": post["author"],
                "chat_type": post["chat_type"],
                "views": post["views"],
                "likes": post["likes"],
                "comments": post["comments"],
                "reactions": post["reactions"],
                "shares": post["shares"],
                "photo_file_id": post["photo_file_id"],
                "photo_width": post["photo_width"],
                "photo_height": post["photo_height"],
                "video_file_id": post["video_file_id"],
                "document_file_id": post["document_file_id"],
                "document_mime_type": post["document_mime_type"],
                "platform": 2  # Bale platform
            }

            # حذف فیلدهای خالی
            api_data = {k: v for k, v in api_data.items() if v is not None}

            response = requests.post(POSTS_CREATE_API_URL, headers=headers, json=api_data)

            if response.status_code in [200, 201]:
                success_count += 1
                print(f"پست {post['post_id']} با موفقیت ارسال شد.")
            else:
                error_count += 1
                print(f"خطا در ارسال پست {post['post_id']}: {response.status_code} - {response.text}")

        except Exception as e:
            error_count += 1
            print(f"خطا در ارسال پست {post.get('post_id', 'unknown')}: {e}")

    print(f"نتایج ارسال: {success_count} موفق, {error_count} خطا")
    return success_count > 0


# تابع برای پردازش تاریخ
def process_date(date_str):
    if not date_str:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        # اگر تاریخ کامل با زمان دارد
        if "T" in date_str and ":" in date_str.split("T")[1]:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # اگر فقط تاریخ دارد
        elif "T" in date_str:
            date_part = date_str.split("T")[0]
            return datetime.fromisoformat(date_part).replace(hour=0, minute=0, second=0)
        # اگر فرمت دیگری دارد
        else:
            return datetime.fromisoformat(date_str).replace(hour=0, minute=0, second=0)
    except (ValueError, AttributeError):
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


# تابع برای استخراج هشتگ‌ها از متن
def extract_hashtags(text):
    if not text:
        return ""
    hashtags = re.findall(r'#\w+', text)
    return " ".join(hashtags)


# تابع برای تبدیل زمان رشته‌ای به شی datetime
def parse_relative_time(time_str, date_tag_gregorian=None):
    now = datetime.now()

    if not time_str:
        return now

    # اگر زمان به صورت "ساعت:دقیقه" است
    if ":" in time_str and len(time_str) <= 5:
        try:
            # استفاده از تاریخ تگ اگر موجود باشد، در غیر این صورت از امروز
            target_date = date_tag_gregorian or now.date()
            hour, minute = map(int, time_str.split(":"))
            return datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))
        except ValueError:
            return now

    # برای سایر فرمت‌ها
    return now


# تابع برای استخراج اطلاعات مدیا از پست
def extract_media_info(element):
    media_info = {
        'photo_file_id': None,
        'photo_width': None,
        'photo_height': None,
        'video_file_id': None,
        'document_file_id': None,
        'document_mime_type': None
    }

    try:
        # بررسی وجود عکس
        img_elements = element.find_elements(By.TAG_NAME, "img")
        for img in img_elements:
            alt_text = img.get_attribute("alt")
            if alt_text == "Photo Message":
                media_info['photo_file_id'] = element.get_attribute("data-sid")
                # سعی در استخراج ابعاد عکس
                try:
                    style = img.get_attribute("style")
                    width_match = re.search(r'width:\s*(\d+)px', style)
                    height_match = re.search(r'height:\s*(\d+)px', style)
                    if width_match:
                        media_info['photo_width'] = int(width_match.group(1))
                    if height_match:
                        media_info['photo_height'] = int(height_match.group(1))
                except:
                    pass
                media_info['document_mime_type'] = 'image/jpeg'
                break

        # بررسی وجود ویدیو
        video_elements = element.find_elements(By.CLASS_NAME, "Thumbnail_image__sqjPX")
        if video_elements:
            media_info['video_file_id'] = element.get_attribute("data-sid")
            media_info['document_mime_type'] = 'video/mp4'

        # بررسی وجود صوت
        audio_elements = element.find_elements(By.CLASS_NAME, "Audio_grid__QGGKd")
        if audio_elements:
            media_info['document_file_id'] = element.get_attribute("data-sid")
            media_info['document_mime_type'] = 'audio/mp3'

    except Exception as e:
        print(f"خطا در استخراج اطلاعات مدیا: {e}")

    return media_info


# تابع برای کرال کردن پست‌ها از صفحه وب
def crawl_posts_from_web(channel_username, start_date, my_id):
    options = Options()
    options.add_argument("--headless")  # اجرای بدون نمایش مرورگر
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    posts_data = []
    current_date_tag = ""  # برای ذخیره آخرین تگ تاریخ مشاهده شده
    current_gregorian_date = None  # برای ذخیره تاریخ میلادی تبدیل شده

    try:
        # رفتن به صفحه کانال
        driver.get(f"https://ble.ir/   {channel_username}")
        print(f"در حال کرال کردن صفحه: https://ble.ir/   {channel_username}")

        # منتظر ماندن تا محتوا لود شود
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-sid]"))
        )
        time.sleep(3)  # منتظر ماندن اضافی برای اطمینان

        # پیدا کردن المنت اسکرول
        try:
            scroll_element = driver.find_element(By.XPATH, '//*[@id="__next"]/div[2]')
        except:
            scroll_element = driver.find_element(By.TAG_NAME, "body")

        last_height = driver.execute_script("return arguments[0].scrollHeight", scroll_element)
        scroll_pause_time = 2
        max_scroll_attempts = 10
        scroll_attempts = 0

        while scroll_attempts < max_scroll_attempts:
            # اسکرول به پایین
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_element)
            time.sleep(scroll_pause_time)

            # بررسی ارتفاع جدید
            new_height = driver.execute_script("return arguments[0].scrollHeight", scroll_element)
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1

        # حالا به بالا برمی‌گردیم و پست‌ها را بررسی می‌کنیم
        driver.execute_script("arguments[0].scrollTop = 0", scroll_element)
        time.sleep(2)

        # پیدا کردن تمام پست‌ها و تگ‌های تاریخ
        all_elements = driver.find_elements(By.CSS_SELECTOR, "[data-sid], time.DateDivider_Date__AwRVR")
        print(f"تعداد المنت‌های یافت شده: {len(all_elements)}")

        for element in all_elements:
            try:
                # بررسی نوع المنت
                if element.get_attribute("data-sid"):  # این یک پست است
                    data_sid = element.get_attribute("data-sid")

                    # استخراج متن پست
                    text_content = ""
                    try:
                        text_elements = element.find_elements(By.CLASS_NAME, "Text_text__7_UOM")
                        text_content = " ".join([elem.text for elem in text_elements if elem.text])
                    except:
                        pass

                    # استخراج زمان پست
                    post_time = ""
                    try:
                        time_element = element.find_element(By.CLASS_NAME, "Info_date__6lwmx")
                        post_time = time_element.text if time_element else ""
                    except:
                        pass

                    # پردازش تاریخ و زمان پست
                    post_datetime = parse_relative_time(post_time, current_gregorian_date)

                    # استخراج هشتگ‌ها
                    hashtags = extract_hashtags(text_content)

                    # استخراج اطلاعات مدیا
                    media_info = extract_media_info(element)

                    # ترکیب تاریخ میلادی و زمان
                    date_time_combined = post_datetime.strftime("%Y-%m-%d %H:%M:%S")

                    # ایجاد message_id از 5 رقم آخر post_id
                    message_id = data_sid[-5:] if data_sid and len(data_sid) >= 5 else data_sid

                    # ذخیره اطلاعات پست با فیلدهای جدید
                    post_data = {
                        "channel": my_id,  # تغییر از my_id به channel
                        "post_id": data_sid,
                        "message_id": message_id,
                        "post_text": text_content,
                        "hashtags": hashtags,
                        "date": date_time_combined,  # ترکیب تاریخ میلادی و زمان
                        "collected_at": post_datetime.strftime("%Y-%m-%d"),  # تاریخ میلادی
                        "author": 1,  # مقدار ثابت author
                        "chat_type": "channel",  # مقدار ثابت chat-type
                        "views": 0,
                        "likes": 0,
                        "comments": 0,
                        "reactions": 0,
                        "shares": 0,
                    }

                    # اضافه کردن اطلاعات مدیا
                    post_data.update(media_info)

                    posts_data.append(post_data)

                elif "DateDivider_Date__AwRVR" in element.get_attribute("class"):  # این یک تگ تاریخ است
                    # استخراج محتوای تگ تاریخ
                    current_date_tag = element.text
                    current_gregorian_date = parse_persian_date(current_date_tag)
                    print(f"تگ تاریخ جدید یافت شد: {current_date_tag} -> {current_gregorian_date}")

            except Exception as e:
                print(f"خطا در پردازش المنت: {e}")
                continue

    except Exception as e:
        print(f"خطا در کرال کردن صفحه وب: {e}")
    finally:
        driver.quit()

    return posts_data


# تابع اصلی
def main():
    print(f"شروع اجرای برنامه در: {datetime.now()}")

    # دریافت لیست کانال‌ها
    channels = get_channels_with_retry()
    if not channels:
        print("هیچ کانالی یافت نشد.")
        return

    all_posts_data = []

    # محدود کردن به ۵ کانال برای تست
    test_channels = channels[1:]
    print(f"تست بر روی {len(test_channels)} کانال")

    # پردازش هر کانال
    for channel in test_channels:
        my_id = channel.get("id")
        channel_username = channel.get("channel_id", f"channel_{my_id}")

        print(f"دریافت پست‌های کانال: {channel_username} (ID: {my_id})")

        # دریافت پست‌ها از API
        posts = get_posts_with_retry(my_id)
        print(posts)

        # پیدا کردن آخرین تاریخ پست از API
        latest_api_date = None
        if posts:
            # پیدا کردن آخرین پست
            latest_post = max(posts, key=lambda x: process_date(x.get("date", x.get("date", ""))))
            print("*********")
            print(latest_post)
            latest_api_date = process_date(latest_post.get("date", latest_post.get("date", "")))
            # print(latest_post)
            print(f"آخرین پست API در تاریخ: {latest_api_date}")
        else:
            # اگر کانال هیچ پستی ندارد
            latest_api_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            print(f"کانال {channel_username} هیچ پستی در API ندارد. استفاده از تاریخ امروز: {latest_api_date}")

        # کرال کردن پست‌ها از صفحه وب
        crawled_posts = crawl_posts_from_web(channel_username, latest_api_date, my_id)

        # فیلتر کردن پست‌های جدیدتر از تاریخ آخرین پست API
        new_posts = []
        for post in crawled_posts:
            post_dt = datetime.strptime(post["date"], "%Y-%m-%d %H:%M:%S")
            print("****************")
            # تعریف منطقه زمانی +03:30 (مثلاً ایران)
            # tehran_tz = timezone(timedelta(hours=0, minutes=0))

            # تبدیل post_dt به aware با منطقه زمانی +03:30
            # post_dt_normalized = (post_dt.replace(tzinfo=tehran_tz))- timedelta(hours=3, minutes=30)
            # latest_api_date_normalized = (latest_api_date.astimezone(tehran_tz)) - timedelta(hours=3, minutes=30)
            print(post_dt)
            print(latest_api_date)
            latest_api_date_naive = latest_api_date.replace(tzinfo=None)
            print(latest_api_date_naive)
            post_dt_naive = post_dt.replace(tzinfo=None)
            print(post_dt_naive)
            print("****************")
            if post_dt_naive > latest_api_date_naive:
                new_posts.append(post)
                print(f"پست جدید یافت شد: {post_dt} > {latest_api_date}")

        all_posts_data.extend(new_posts)
        print(f"تعداد پست‌های جدید برای کانال {channel_username}: {len(new_posts)}")

    # ارسال داده‌ها به API به جای ذخیره در اکسل
    if all_posts_data:
        print(f"در حال ارسال {len(all_posts_data)} پست جدید به API...")
        send_posts_to_api(all_posts_data)
    else:
        print("هیچ پست جدیدی یافت نشد.")

    print(f"اتمام اجرای برنامه در: {datetime.now()}")


# تابع برای اجرای زمان‌بندی شده
def run_scheduled_job():
    try:
        main()
    except Exception as e:
        print(f"خطا در اجرای برنامه: {e}")


if __name__ == "__main__":
    # زمان‌بندی اجرای برنامه هر یک ساعت
    schedule.every(1).hours.do(run_scheduled_job)

    # اجرای اولیه بلافاصله پس از راه‌اندازی
    print("برنامه در حال راه‌اندازی...")
    run_scheduled_job()

    # حلقه بی‌نهایت برای اجرای زمان‌بندی
    while True:
        schedule.run_pending()
        time.sleep(60)  # بررسی هر 60 ثانیه