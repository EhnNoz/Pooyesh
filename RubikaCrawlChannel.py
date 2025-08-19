import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import pandas as pd
from datetime import datetime, timedelta
from persiantools.jdatetime import JalaliDate
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
# --- تنظیمات API ---
BASE_API_URL = os.getenv("BASE_API_URL")
LOGIN_URL = f"{BASE_API_URL}/token/"
CHANNEL_API_URL = f"{BASE_API_URL}/rep/channel-code/?platform=4"  # platform=4 for Rubika
POST_API_URL = f"{BASE_API_URL}/rep/posts/"
POSTS_API_URL = f"{BASE_API_URL}/rep/posts/?platform=4&channel={{id}}"

# --- اطلاعات ورود به API ---
# print(os.getenv("API_USERNAME"))
API_USERNAME = os.getenv("API_USERNAME")  # جایگزین خط قدیمی
API_PASSWORD = os.getenv("API_PASSWORD")  # جایگزین خط قدیمی
access_token = None

print("🚀 شروع اسکریپت...")


# --- لاگین به API و دریافت توکن ---
def login_to_api():
    global access_token
    try:
        response = requests.post(LOGIN_URL, data={
            "username": API_USERNAME,
            "password": API_PASSWORD
        })
        response.raise_for_status()
        access_token = response.json().get("access")
        print("✅ با موفقیت به API لاگین شد.")
        return True
    except Exception as e:
        print(f"❌ خطا در لاگین به API: {str(e)}")
        return False


# --- دریافت لیست کانال‌ها از API ---
def get_channels():
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(CHANNEL_API_URL, headers=headers)
        response.raise_for_status()
        channels = response.json()
        print(f"✅ تعداد {len(channels)} کانال دریافت شد.")
        return channels
    except Exception as e:
        print(f"❌ خطا در دریافت کانال‌ها: {str(e)}")
        return []


# --- دریافت آخرین تاریخ پست یک کانال ---
def get_last_post_date(channel_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        url = POSTS_API_URL.format(id=channel_id)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        posts = response.json()
        if posts:
            last_post_date = posts[-1].get("date")
            print(f"آخرین پست کانال {channel_id} در تاریخ {last_post_date}")
            return last_post_date
        return None
    except Exception as e:
        print(f"❌ خطا در دریافت آخرین پست: {str(e)}")
        return None


# --- ارسال پست‌ها به API ---
def normalize_datetime(dt_str):
    """یکسان‌سازی فرمت تاریخ‌های مختلف به فرمت استاندارد"""
    dt_str = re.sub(r'[+-]\d{2}:\d{2}$', '', dt_str)
    dt_str = dt_str.replace('T', ' ')
    dt_str = re.sub(r'\.\d+', '', dt_str)
    return dt_str.strip()


def send_posts_to_api(posts, last_post_date=None):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    success_count = 0

    if last_post_date is None:
        posts = posts[-50:]

    for post in posts:
        try:
            normalized_post_date = normalize_datetime(post["date"])
            post_datetime = datetime.strptime(normalized_post_date, "%Y-%m-%d %H:%M:%S")

            last_post_datetime = None
            if last_post_date:
                normalized_last_date = normalize_datetime(last_post_date)
                last_post_datetime = datetime.strptime(normalized_last_date, "%Y-%m-%d %H:%M:%S")

            if last_post_datetime is None or post_datetime > last_post_datetime:
                post_to_send = post.copy()
                post_to_send["message_id"] = 0

                print(f"ارسال پست با تاریخ: {post['date']}")
                response = requests.post(POST_API_URL, json=post_to_send, headers=headers)
                response.raise_for_status()
                success_count += 1
            else:
                print(f"⏩ پست با تاریخ {post['date']} قبلاً ارسال شده است (رد شد)")

        except Exception as e:
            print(f"❌ خطا در پردازش پست: {str(e)}")
            continue

    print(f"✅ {success_count} از {len(posts)} پست جدید با موفقیت ارسال شد.")
    return success_count > 0


# --- توابع کمکی ---
def persian_date_to_gregorian(persian_date_str):
    try:
        persian_date_str = persian_date_str.split('، ')[1].strip()
        parts = persian_date_str.split(' ')
        day = int(parts[0])
        month_name = parts[1]
        year = int(parts[2])

        month_names = {
            'فروردین': 1, 'اردیبهشت': 2, 'خرداد': 3, 'تیر': 4, 'مرداد': 5,
            'شهریور': 6, 'مهر': 7, 'آبان': 8, 'آذر': 9, 'دی': 10,
            'بهمن': 11, 'اسفند': 12
        }
        month = month_names.get(month_name, 1)

        jalali_date = JalaliDate(year, month, day)
        return jalali_date.to_gregorian().strftime('%Y-%m-%d')
    except:
        return None


def extract_hashtags(text):
    if not text:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = re.sub(r'https?://\S+|www\.\S+', '', clean_text)
    hashtags = re.findall(r'(#\w[^\s#<>،:;.!?\u200c]*)', clean_text)
    valid_hashtags = []
    for tag in hashtags:
        clean_tag = re.sub(r'[^\w\u0600-\u06FF\-_#]+$', '', tag)
        if len(clean_tag) > 1:
            valid_hashtags.append(clean_tag)
    return ' '.join(valid_hashtags) if valid_hashtags else ""


def clean_post_text(raw_html):
    if not raw_html:
        return "(بدون متن)"
    cleaned_text = re.sub(r'<div class="reactions reactions-block">.*?</div>', '', raw_html, flags=re.DOTALL)
    cleaned_text = re.sub(r'<a\b[^>]*>(.*?)</a>', '', cleaned_text)
    cleaned_text = re.sub(r'<div[^>]*>|</div>', '', cleaned_text)
    cleaned_text = re.sub(r'<span[^>]*>.*?</span>', '', cleaned_text)
    cleaned_text = re.sub(r':[a-z_]+:', '', cleaned_text)
    cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)
    cleaned_text = re.sub(r'https?://\S+|www\.\S+', '', cleaned_text)
    cleaned_text = re.sub(r'@\w+', '', cleaned_text)
    cleaned_text = re.sub(r'[\u200c\u200e\u200f]', '', cleaned_text)
    cleaned_text = re.sub(r'[^\w\s\u0600-\u06FF\uFB8A\u067E\u0686\u06AF\u200C\u200F.,،:;!?ـ]', '', cleaned_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    patterns = [
        r':point_down:.*',
        r':point_up_2:.*',
        r':bangbang:.*',
        r':rotating_light:.*'
    ]
    for pattern in patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text)
    cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text)
    return cleaned_text.strip() or "(بدون متن)"


# --- لاگین به API ---
if not login_to_api():
    exit()

# --- دریافت کانال‌ها ---
channels = get_channels()
if not channels:
    exit()

# --- تنظیمات مرورگر ---
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
# options.add_argument("--headless")

try:
    driver = webdriver.Chrome(options=options)
    print("✅ مرورگر Chrome با موفقیت راه‌اندازی شد.")
except Exception as e:
    print("❌ خطا در راه‌اندازی مرورگر:", str(e))
    exit()

# --- پردازش هر کانال ---
first_channel = True

for channel in channels:
    channel_id = channel.get("channel_id")
    channel_name = channel.get("name", "بدون نام")
    my_id = channel.get("id")
    print(f"\n🔍 شروع پردازش کانال: {channel_name} (ID: {channel_id})")

    # --- دریافت آخرین تاریخ پست ---
    last_post_date = get_last_post_date(my_id)

    # --- باز کردن صفحه کانال ---
    url = f"https://web.rubika.ir/#c={channel_id}"
    print(f"🌐 در حال باز کردن: {url}")

    # ابتدا صفحه اصلی را بارگذاری کنید
    driver.get("https://web.rubika.ir/")
    time.sleep(2)

    # سپس به کانال مورد نظر بروید
    driver.get(url)
    time.sleep(5)

    # --- ورود دستی فقط برای اولین کانال ---
    if first_channel:
        print("⏳ لطفاً دستی وارد حساب کاربری خود شوید (30 ثانیه فرصت دارید)...")
        time.sleep(30)
        first_channel = False
    else:
        time.sleep(10)

    # بررسی اینکه آیا در صفحه صحیح هستیم
    current_url = driver.current_url
    print(f"آدرس فعلی: {current_url}")

    if f"c={channel_id}" not in current_url:
        print(f"❌ خطا در بارگذاری کانال {channel_id}")
        print("تلاش مجدد...")
        driver.get(url)
        time.sleep(10)

        if f"c={channel_id}" not in driver.current_url:
            print(f"❌❌ خطای جدی: نتوانستیم به کانال {channel_id} برویم. رد شدن از این کانال...")
            continue

    # --- پیدا کردن کانتینر پیام‌ها ---
    print("🔍 در حال یافتن کانتینر اسکرول...")
    try:
        chat_container = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".scrollable.scrollable-y")))
        print("✅ کانتینر اسکرول پیدا شد.")
    except TimeoutException:
        print("❌ کانتینر اسکرول پیدا نشد.")
        continue

    # --- قرار دادن موس در موقعیت مناسب ---
    print("\n⚠️ قرار دادن موس در وسط کانتینر...")
    try:
        first_message = chat_container.find_element(By.CSS_SELECTOR, "[data-msg-id]")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_message)
        time.sleep(2)
    except:
        print("⚠️ نتوانستم پیامی برای قرار دادن موس پیدا کنم، ادامه می‌دهم...")

    # --- شروع جمع‌آوری پیام‌ها ---
    seen_msg_ids = set()
    messages_data = []
    scroll_count = 0
    current_date = datetime.now().date()
    last_processed_date = None
    reached_last_post = False

    print("🔄 شروع اسکرول به بالا برای بارگذاری پیام‌ها...")

    while not reached_last_post:
        scroll_count += 1
        print(f"\n--- اسکرول شماره {scroll_count} ---")

        prev_scroll_top = driver.execute_script("return arguments[0].scrollTop;", chat_container)
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop - 500;", chat_container)
        time.sleep(2)

        try:
            new_elements = driver.find_elements(By.CSS_SELECTOR, "[data-msg-id], .bubble.service.is-date")
            new_messages_found = False

            for el in new_elements:
                if 'is-date' in el.get_attribute('class'):
                    try:
                        date_text = el.find_element(By.CSS_SELECTOR, 'span').text
                        gregorian_date = persian_date_to_gregorian(date_text)
                        if gregorian_date:
                            current_date = datetime.strptime(gregorian_date, '%Y-%m-%d').date()
                            last_processed_date = current_date

                            if last_post_date and current_date <= datetime.strptime(last_post_date, '%Y-%m-%d').date():
                                print(f"✅ به تاریخ آخرین پست ({last_post_date}) رسیدیم.")
                                reached_last_post = True
                                break
                    except:
                        continue
                else:
                    msg_id = el.get_attribute("data-msg-id")
                    if msg_id and msg_id not in seen_msg_ids:
                        seen_msg_ids.add(msg_id)
                        new_messages_found = True

            if reached_last_post:
                break

        except:
            new_messages_found = False

        current_scroll_top = driver.execute_script("return arguments[0].scrollTop;", chat_container)

        if current_scroll_top == prev_scroll_top:
            if not new_messages_found:
                print("⏳ اسکرول تغییری نکرد. بررسی نهایی...")
                time.sleep(3)

                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop - 100;", chat_container)
                time.sleep(2)

                current_scroll_top = driver.execute_script("return arguments[0].scrollTop;", chat_container)
                if current_scroll_top == prev_scroll_top:
                    print("⏸️ به نظر می‌رسد به ابتدای تاریخچه رسیده‌ایم.")
                    break
            else:
                print("🔍 پیام‌های جدید پیدا شد، ادامه اسکرول...")
        else:
            print(f"📊 مجموع پیام‌های یکتا: {len(seen_msg_ids)}")

    # --- استخراج نهایی پیام‌ها ---
    print("\n📥 در حال استخراج نهایی پیام‌ها...")
    all_elements = driver.find_elements(By.CSS_SELECTOR, ".bubbles-group[data-msg-id], .bubble.service.is-date")

    current_date = datetime.now().date()
    last_processed_date = None

    for elem in all_elements:
        try:
            if 'is-date' in elem.get_attribute('class'):
                try:
                    date_text = elem.find_element(By.CSS_SELECTOR, 'span').text
                    gregorian_date = persian_date_to_gregorian(date_text)
                    if gregorian_date:
                        current_date = datetime.strptime(gregorian_date, '%Y-%m-%d').date()
                        last_processed_date = current_date
                except:
                    continue
            else:
                msg_id = elem.get_attribute("data-msg-id")
                if not msg_id:
                    continue

                raw_html = ""
                try:
                    try:
                        text_elem = elem.find_element(By.CSS_SELECTOR, "[rb-message-text] div[rb-copyable]")
                        raw_html = text_elem.get_attribute("innerHTML")
                    except:
                        content_div = elem.find_element(By.CSS_SELECTOR, ".message > div, .message-wrapper > div")
                        raw_html = content_div.get_attribute("innerHTML")
                except:
                    pass

                caption = clean_post_text(raw_html)
                hashtags = extract_hashtags(raw_html)

                forward_from_chat_title = None
                try:
                    forward_elem = elem.find_element(By.CSS_SELECTOR, ".im_message_fwd_author")
                    forward_from_chat_title = forward_elem.text.strip()
                except:
                    pass

                has_media = False
                try:
                    media_elem = elem.find_element(By.CSS_SELECTOR, ".media-photo")
                    has_media = True
                except:
                    pass

                views = 0
                time_str = "00:00"
                try:
                    time_elem = elem.find_element(By.CSS_SELECTOR, "span[rb-message-time]")
                    inner_html = ""
                    try:
                        inner_div = time_elem.find_element(By.CSS_SELECTOR, "div.inner.rbico")
                        inner_html = inner_div.get_attribute("innerHTML")
                    except:
                        inner_html = time_elem.get_attribute("innerHTML")

                    views_match = re.search(r'(\d[\d.,]*)\s*<!-{2,}>\s*<!-{2,}>\s*<i[^>]+rbico-channelviews',
                                            inner_html)
                    if not views_match:
                        views_match = re.search(r'(\d[\d.,]*)\s*<i[^>]+rbico-channelviews', inner_html)
                    if views_match:
                        v = views_match.group(1).replace('M', '000000').replace('K', '000').replace('.', '')
                        views = int(v) if v.isdigit() else 0

                    time_match = re.search(r'<span>(\d{1,2}:\d{2})</span>', inner_html)
                    time_str = time_match.group(1) if time_match else "00:00"
                except:
                    pass

                message_date = current_date

                if last_processed_date is None and current_date == datetime.now().date():
                    message_date = current_date - timedelta(days=1)

                try:
                    hour, minute = map(int, time_str.split(':'))
                    datetime_combined = datetime.combine(message_date, datetime.min.time()).replace(hour=hour,
                                                                                                    minute=minute)
                    datetime_str = datetime_combined.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    datetime_str = f"{message_date.strftime('%Y-%m-%d')} 00:00:00"

                if msg_id not in [d["message_id"] for d in messages_data]:
                    messages_data.append({
                        "message_id": msg_id,
                        "date": datetime_str,
                        "post_text": caption,
                        "hashtags": hashtags,
                        "views": views,
                        "sender_name": channel_name,
                        "sender_username": channel_id,
                        "chat_id": channel_id,
                        "chat_type": "channel",
                        "has_media": has_media,
                        "forward_from_chat_title": forward_from_chat_title,
                        "collected_at": datetime_combined.strftime('%Y-%m-%d'),
                        "author": 1,
                        "channel": my_id
                    })

        except Exception as e:
            print(f"❌ خطا در پردازش پیام: {str(e)}")
            continue

    # --- ارسال پست‌ها به API ---
    if messages_data:
        print(f"\n📤 در حال ارسال پست‌های جدید به API...")
        if send_posts_to_api(messages_data, last_post_date):
            print(f"✅ پست‌های جدید کانال {channel_name} با موفقیت ارسال شدند.")
        else:
            print(f"❌ خطا در ارسال پست‌های کانال {channel_name}.")
    else:
        print("ℹ️ هیچ پست جدیدی برای ارسال پیدا نشد.")

# --- پایان کار ---
print("\n🔚 اسکریپت با موفقیت انجام شد.")
# driver.quit()