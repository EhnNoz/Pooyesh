import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
import re
from datetime import time as tme
from datetime import datetime, timedelta
import jdatetime
import schedule

# --- تنظیمات API ---
LOGIN_URL = "http://185.204.197.17:8000/sapi/token/"
CHANNEL_API_URL = "http://185.204.197.17:8000/sapi/rep/channel-code/?platform=1"
POSTS_API_URL = "http://185.204.197.17:8000/sapi/rep/posts/?platform=1&channel="
POST_API_URL = "http://185.204.197.17:8000/sapi/rep/posts/"

# --- توکن احراز هویت ---
HEADERS = {
    "Content-Type": "application/json"
}

def set_auth_header(access_token):
    """تنظیم هدر با access token"""
    HEADERS["Authorization"] = f"Bearer {access_token}"

# --- 1️⃣ ورود و گرفتن توکن ---
def get_jwt_tokens(username, password):
    """
    ارسال username و password و گرفتن JWT
    """
    login_data = {
        "username": username,
        "password": password
    }
    try:
        response = requests.post(LOGIN_URL, data=login_data)
        response.raise_for_status()
        tokens = response.json()
        print("✅ ورود موفقیت‌آمیز")
        return tokens['access']
    except requests.exceptions.HTTPError as err:
        print(f"❌ خطا در ورود (کد {response.status_code}): {response.text}")
        return None
    except Exception as e:
        print(f"❌ خطا در اتصال به API ورود: {e}")
        return None

# --- 2️⃣ دریافت لیست کانال‌ها با احراز هویت ---
def get_channels_from_api(access_token):
    """دریافت لیست کانال‌ها با استفاده از توکن احراز هویت"""
    try:
        set_auth_header(access_token)
        response = requests.get(CHANNEL_API_URL, headers=HEADERS)
        response.raise_for_status()
        channels = response.json()
        print(f"✅ تعداد {len(channels)} کانال دریافت شد")
        return channels
    except requests.exceptions.HTTPError as err:
        print(f"❌ خطا در دریافت کانال‌ها (کد {response.status_code}): {response.text}")
        return []
    except Exception as e:
        print(f"❌ خطا در اتصال به API کانال‌ها: {e}")
        return []

# --- دریافت آخرین پست هر کانال از API ---
def get_last_post_info(channel_id, access_token):
    """دریافت آخرین پست کانال از طریق API"""
    try:
        set_auth_header(access_token)
        url = f"{POSTS_API_URL}{channel_id}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        posts = response.json()
        if not posts:
            print(f"⚠️ هیچ پستی برای کانال {channel_id} یافت نشد")
            return None, None
        # آخرین پست بر اساس date
        last_post = max(posts, key=lambda x: x['date'])
        print(f"✅ آخرین پست کانال {channel_id}: message_id={last_post['message_id']}, sent_at={last_post['date']}")
        return last_post['message_id'], last_post['date']
    except requests.exceptions.HTTPError as err:
        print(f"❌ خطا در دریافت پست‌های کانال {channel_id} (کد {response.status_code}): {response.text}")
        return None, None
    except Exception as e:
        print(f"❌ خطا در اتصال به API پست‌ها برای کانال {channel_id}: {e}")
        return None, None

# --- تبدیل اعداد فارسی/عربی به انگلیسی ---
def persian_to_english(s):
    translation_table = str.maketrans(
        '۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩',
        '01234567890123456789'
    )
    return s.translate(translation_table)

# --- تبدیل ماه فارسی به عدد ---
persian_months = {
    'فروردین': 1, 'اردیبهشت': 2, 'خرداد': 3,
    'تیر': 4, 'مرداد': 5, 'شهریور': 6,
    'مهر': 7, 'آبان': 8, 'آذر': 9,
    'دی': 10, 'بهمن': 11, 'اسفند': 12
}

# --- تبدیل معکوس: عدد به نام ماه فارسی ---
reverse_persian_months = {v: k for k, v in persian_months.items()}

# --- تشخیص تاریخ واقعی از عباراتی مثل "امروز" ---
def get_shamsi_date(persian_date_str):
    if not persian_date_str:
        return None
    persian_date_str = persian_date_str.strip()
    today = jdatetime.date.today()
    if persian_date_str == "امروز":
        return f"{today.day} {reverse_persian_months[today.month]}"
    elif persian_date_str == "دیروز":
        yesterday = today - jdatetime.timedelta(days=1)
        return f"{yesterday.day} {reverse_persian_months[yesterday.month]}"
    else:
        try:
            day_str, month_name = persian_date_str.split()
            day = int(persian_to_english(day_str))
            month = persian_months[month_name]
            return f"{day} {month_name}"
        except:
            return f"{today.day} {reverse_persian_months[today.month]}"

# --- تبدیل تاریخ شمسی به میلادی ---
def shamsi_to_miladi(persian_date_str):
    try:
        day_str, month_name = persian_date_str.strip().split()
        day = int(persian_to_english(day_str))
        month = persian_months[month_name]
        year = jdatetime.date.today().year
        today = jdatetime.date.today()
        if month > today.month or (month == today.month and day > today.day):
            year -= 1
        return jdatetime.date(year, month, day).togregorian()
    except Exception as e:
        print(f"⚠️ خطای تبدیل تاریخ: {e}")
        return datetime(1970, 1, 1).date()

# --- استخراج هشتگ‌ها ---
def extract_hashtags(text):
    hashtags = re.findall(r'#\S+', text)
    return ' '.join(hashtags) if hashtags else ""

# --- تنظیمات مرورگر ---
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")  # فعال کنید اگر بدون نمایش اجرا شود
    return webdriver.Chrome(options=options)

def process_channel_data(channel_data):
    """پردازش و اصلاح داده‌های کانال"""
    today = datetime.now()
    corrected_count = 0
    for item in channel_data:
        try:
            # تبدیل رشته تاریخ به شیء datetime
            item['sent_at_datetime'] = datetime.strptime(item['sent_at'], "%Y-%m-%d %H:%M:%S")
            # بررسی آیا تاریخ در آینده است
            item['is_future_date'] = item['sent_at_datetime'] > today
            # اگر تاریخ در آینده بود، اصلاح کن
            if item['is_future_date']:
                corrected_count += 1
                original_date = item['sent_at_datetime']
                # اصلاح تاریخ با کم کردن یک روز
                item['sent_at_datetime'] = original_date - timedelta(days=1)
                item['sent_at'] = item['sent_at_datetime'].strftime("%Y-%m-%d %H:%M:%S")
                # ذخیره تاریخ اصلی برای اطلاع رسانی
                item['original_date'] = original_date.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"خطا در پردازش تاریخ: {e}")
            item['is_future_date'] = False
    # گزارش اصلاحات
    if corrected_count > 0:
        print(f"✅ تعداد {corrected_count} تاریخ آینده شناسایی و اصلاح شدند")
    return channel_data

def send_posts_to_api(posts_data, access_token):
    """ارسال پست‌ها به API"""
    if not posts_data:
        print("⚠️ هیچ داده‌ای برای ارسال وجود ندارد")
        return True
    success_count = 0
    failure_count = 0
    for post in posts_data:
        payload = {
            "channel": post.get('my_id', ''),
            "author": 1,
            "post_text": post.get('text', ''),
            "views": post.get('views', 0),
            "date": post.get('sent_at', ''),
            "hashtags": post.get('hashtags', ''),
            "collected_at": post.get('collected_at', ''),
            "message_id": post.get('message_id', 0)
        }
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            response = requests.post(POST_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            success_count += 1
            print(f"✅ پست با message_id {payload['message_id']} با موفقیت ارسال شد")
        except requests.exceptions.HTTPError as err:
            if response.status_code == 401:
                print("❌ توکن منقضی شده، لطفاً دوباره وارد شوید")
                return False
            print(f"❌ خطا در ارسال پست {payload['message_id']} (کد {response.status_code}): {response.text}")
            failure_count += 1
        except Exception as e:
            print(f"❌ خطای غیرمنتظره در ارسال پست {payload['message_id']}: {e}")
            failure_count += 1
    print(f"📊 نتیجه ارسال: {success_count} موفق, {failure_count} ناموفق")
    return failure_count == 0

# --- تابع اصلی کرال هر کانال ---
def crawl_channel(driver, channel_id, channel_name, my_id, last_sent_at=None):
    url = f"https://eitaa.com/{channel_id.replace('@', '')}/"
    driver.get(url)
    time.sleep(10)
    collected_data = []
    seen_keys = set()
    no_new_data_count = 0
    max_no_data_retries = 3
    last_detected_date = None
    reached_target = False

    target_datetime = None
    if last_sent_at:
        print(f"⏳ کرال از پست‌های جدیدتر از: {last_sent_at}")
        try:
            datetime_str = last_sent_at.split('+')[0] if '+' in last_sent_at else last_sent_at.split('.')[0]
            target_datetime = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
        except Exception as e:
            print(f"⚠️ خطا در تبدیل تاریخ آخرین پست: {last_sent_at}")
            print(e)

    while no_new_data_count < max_no_data_retries and not reached_target:
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.HOME)
            print(f"اسکرول به بالا در کانال {channel_id}...")
            try:
                date_element = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, "etme_widget_message_service_date"))
                )
                raw_date = date_element.text.strip()
                last_detected_date = get_shamsi_date(raw_date)
                print(f"📅 تاریخ موقت: '{raw_date}' → '{last_detected_date}'")
            except Exception:
                print(f"هشدار: تاریخ موقت پیدا نشد. استفاده از: {last_detected_date}")

            try:
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.CLASS_NAME, "loading-spinner"))
                )
                print("بارگذاری کامل شد.")
            except TimeoutException:
                print("هشدار: اسپینر دیده نشد یا زمان‌بندی شد.")

            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CLASS_NAME, "etme_widget_message_bubble")) > 0
            )

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            messages = soup.find_all("div", class_="etme_widget_message_bubble")
            new_items = 0

            for msg in messages:
                text_elem = msg.find("div", class_="etme_widget_message_text js-message_text")
                time_elem = msg.find("time", class_="time")
                views_span = msg.find("span", class_="etme_widget_message_views")

                if not text_elem or not time_elem:
                    continue

                text = text_elem.get_text(strip=True)
                timestamp = time_elem.get_text(strip=True)
                clean_time = persian_to_english(timestamp)
                hour, minute = map(int, clean_time.split(":"))
                post_time = tme(hour, minute)
                views = int(views_span['data-count']) if views_span and views_span.has_attr('data-count') else 0

                effective_date = last_detected_date or "نامشخص"

                try:
                    day_str, month_name = effective_date.split()
                    day = int(persian_to_english(day_str))
                    month = persian_months[month_name]
                    year = jdatetime.date.today().year
                    today = jdatetime.date.today()
                    if month > today.month or (month == today.month and day > today.day):
                        year -= 1
                    gregorian_date = jdatetime.date(year, month, day).togregorian()
                    sent_datetime = datetime.combine(gregorian_date, post_time)
                except Exception as e:
                    print(f"⚠️ خطا در پردازش تاریخ: {e}")
                    sent_datetime = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)

                if target_datetime and sent_datetime <= target_datetime:
                    reached_target = True
                    print(f"🛑 متوقف شد: رسید به پست قدیمی‌تر از {target_datetime}")
                    break

                key = (text, post_time)
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                hashtags = extract_hashtags(text)
                collected_data.append({
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "text": text,
                    "timestamp": post_time.strftime("%H:%M"),
                    "views": views,
                    "date": effective_date,
                    "hashtags": hashtags,
                    "collected_at": datetime.now().strftime("%Y-%m-%d"),
                    "sent_at": sent_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "my_id": my_id
                })
                new_items += 1

            if new_items == 0:
                no_new_data_count += 1
                print(f"داده جدیدی نیومد. تلاش {no_new_data_count}/{max_no_data_retries}")
            else:
                no_new_data_count = 0
                print(f"✅ {new_items} داده جدید اضافه شد. مجموع: {len(collected_data)}")

            time.sleep(random.uniform(3, 6))
        except Exception as e:
            print(f"❌ خطای کلی: {e}")
            no_new_data_count += 1
            time.sleep(2)

    return collected_data

# ================================
# 🔁 تابع اصلی اجرا (هر 6 ساعت یکبار)
# ================================
def run_crawler():
    print(f"\n🔄 شروع اجرای کرال در {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    username = "su-admin"
    password = "SuAdmin@1404"

    access_token = get_jwt_tokens(username, password)
    if not access_token:
        print("❌ امکان ادامه بدون احراز هویت وجود ندارد")
        return

    channels = get_channels_from_api(access_token)
    if not channels:
        print("❌ هیچ کانالی برای کرال یافت نشد")
        return

    driver = setup_driver()
    all_data = []

    try:
        for channel in channels:
            channel_id = channel['channel_id']
            channel_name = channel['name']
            my_id = channel['id']
            print(f"\n🔍 شروع کرال کانال: {channel_name} ({channel_id})")

            last_message_id, last_sent_at = get_last_post_info(my_id, access_token)
            if last_message_id is None and last_sent_at is None:
                print(f"⏭️ هیچ پستی برای کانال {channel_id} یافت نشد. رد شدن...")
                continue

            channel_data = crawl_channel(driver, channel_id, channel_name, my_id, last_sent_at)
            channel_data = process_channel_data(channel_data)
            channel_data.sort(key=lambda x: x['sent_at_datetime'])

            current_message_id = last_message_id + 1 if last_message_id else 1
            for item in channel_data:
                sent_date = item['sent_at'].split()[0]
                item['collected_at'] = sent_date
                item['message_id'] = current_message_id
                current_message_id += 1
                del item['sent_at_datetime']
                if 'original_date' in item:
                    del item['original_date']

            channel_data.sort(key=lambda x: x['message_id'], reverse=True)
            all_data.extend(channel_data)
            print(f"✅ تکمیل کرال کانال {channel_id}. تعداد داده‌های جدید: {len(channel_data)}")

            if not send_posts_to_api(channel_data, access_token):
                print("⏳ تلاش برای دریافت توکن جدید...")
                new_token = get_jwt_tokens(username, password)
                if new_token:
                    access_token = new_token
                    if not send_posts_to_api(channel_data, access_token):
                        print("❌ ارسال مجدد با توکن جدید نیز ناموفق بود")
                else:
                    print("❌ دریافت توکن جدید ناموفق بود")

            time.sleep(random.uniform(3, 6))

    except Exception as e:
        print(f"❌ خطای جدی در حین اجرا: {e}")
    finally:
        driver.quit()

    if all_data:
        df = pd.DataFrame(all_data)
        output_file = f"eitaa_channels_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ داده‌ها در فایل {output_file} ذخیره شدند.")
        print(f"📊 مجموع داده‌های جمع‌آوری شده: {len(df)} از {len(channels)} کانال")
    else:
        print("❌ هیچ داده‌ای جمع‌آوری نشد")

# ================================
# 🕒 برنامه‌ریزی اجرا هر 6 ساعت
# ================================
if __name__ == "__main__":
    # اولین اجرا را فوری انجام بده
    run_crawler()

    # برنامه‌ریزی برای اجرای بعدی هر 6 ساعت
    schedule.every(12).hours.do(run_crawler)

    print("⏰ برنامه به صورت خودکار هر 6 ساعت اجرا می‌شود...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # هر دقیقه چک می‌کند