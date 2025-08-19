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
import schedule
import logging
import traceback

# تنظیمات لاگ‌گیری
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rubika_crawler.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv(dotenv_path=".env")
# --- تنظیمات API ---
BASE_API_URL = os.getenv("BASE_API_URL")
LOGIN_URL = f"{BASE_API_URL}/token/"
CHANNEL_API_URL = f"{BASE_API_URL}/rep/channel-code/?platform=4"  # platform=4 for Rubika
POST_API_URL = f"{BASE_API_URL}/rep/posts/"
POSTS_API_URL = f"{BASE_API_URL}/rep/posts/?platform=4&channel={{id}}"

# --- اطلاعات ورود به API ---
API_USERNAME = os.getenv("API_USERNAME")
API_PASSWORD = os.getenv("API_PASSWORD")
access_token = None

# --- متغیرهای سراسری ---
driver = None
is_logged_in = False
first_channel = True


def setup_driver():
    """تنظیم و راه‌اندازی مرورگر (فقط یک بار)"""
    global driver
    if driver is None:
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # options.add_argument("--headless")  # در صورت نیاز می‌توانید فعال کنید

        try:
            driver = webdriver.Chrome(options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("✅ مرورگر Chrome با موفقیت راه‌اندازی شد.")
            return True
        except Exception as e:
            logger.error(f"❌ خطا در راه‌اندازی مرورگر: {str(e)}")
            return False
    return True


def manual_login():
    """ورود دستی به روبیکا (فقط یک بار)"""
    global is_logged_in

    if is_logged_in:
        return True

    logger.info("⏳ لطفاً دستی وارد حساب کاربری روبیکا خود شوید (30 ثانیه فرصت دارید)...")

    # باز کردن صفحه اصلی روبیکا
    driver.get("https://web.rubika.ir/")
    time.sleep(5)

    # منتظر ماندن برای ورود کاربر
    for i in range(30):
        try:
            # بررسی آیا کاربر لاگین کرده (با چک کردن وجود عناصر خاص بعد از لاگین)
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".sidebar, .chats-list"))
            )
            is_logged_in = True
            logger.info("✅ ورود به روبیکا با موفقیت انجام شد.")
            return True
        except:
            time.sleep(1)

    logger.error("❌ زمان ورود به پایان رسید. لطفاً در اجرای بعدی وارد شوید.")
    return False


def login_to_api():
    """لاگین به API و دریافت توکن"""
    global access_token
    try:
        response = requests.post(LOGIN_URL, data={
            "username": API_USERNAME,
            "password": API_PASSWORD
        })
        response.raise_for_status()
        access_token = response.json().get("access")
        logger.info("✅ با موفقیت به API لاگین شد.")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در لاگین به API: {str(e)}")
        return False


def get_channels():
    """دریافت لیست کانال‌ها از API"""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(CHANNEL_API_URL, headers=headers)
        response.raise_for_status()
        channels = response.json()
        logger.info(f"✅ تعداد {len(channels)} کانال دریافت شد.")
        return channels
    except Exception as e:
        logger.error(f"❌ خطا در دریافت کانال‌ها: {str(e)}")
        return []


def get_last_post_date(channel_id):
    """دریافت آخرین تاریخ پست یک کانال"""
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        url = POSTS_API_URL.format(id=channel_id)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        posts = response.json()
        if posts:
            last_post_date = posts[-1].get("date")
            logger.info(f"آخرین پست کانال {channel_id} در تاریخ {last_post_date}")
            return last_post_date
        return None
    except Exception as e:
        logger.error(f"❌ خطا در دریافت آخرین پست: {str(e)}")
        return None


def normalize_datetime(dt_str):
    """یکسان‌سازی فرمت تاریخ‌های مختلف به فرمت استاندارد"""
    dt_str = re.sub(r'[+-]\d{2}:\d{2}$', '', dt_str)
    dt_str = dt_str.replace('T', ' ')
    dt_str = re.sub(r'\.\d+', '', dt_str)
    return dt_str.strip()


def send_posts_to_api(posts, last_post_date=None):
    """ارسال پست‌ها به API"""
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

                logger.info(f"ارسال پست با تاریخ: {post['date']}")
                response = requests.post(POST_API_URL, json=post_to_send, headers=headers)
                response.raise_for_status()
                success_count += 1
            else:
                logger.info(f"⏩ پست با تاریخ {post['date']} قبلاً ارسال شده است (رد شد)")

        except Exception as e:
            logger.error(f"❌ خطا در پردازش پست: {str(e)}")
            continue

    logger.info(f"✅ {success_count} از {len(posts)} پست جدید با موفقیت ارسال شد.")
    return success_count > 0


def persian_date_to_gregorian(persian_date_str):
    """تبدیل تاریخ شمسی به میلادی"""
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
    """استخراج هشتگ‌ها از متن"""
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
    """پاک‌سازی متن پست"""
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


def process_channel(channel):
    """پردازش یک کانال"""
    global first_channel

    channel_id = channel.get("channel_id")
    channel_name = channel.get("name", "بدون نام")
    my_id = channel.get("id")
    logger.info(f"\n🔍 شروع پردازش کانال: {channel_name} (ID: {channel_id})")

    # دریافت آخرین تاریخ پست
    last_post_date = get_last_post_date(my_id)

    # باز کردن صفحه کانال
    url = f"https://web.rubika.ir/#c={channel_id}"
    logger.info(f"🌐 در حال باز کردن: {url}")

    # بازگشت به صفحه اصلی قبل از رفتن به کانال
    driver.get("https://web.rubika.ir/")
    time.sleep(2)

    # رفتن به کانال مورد نظر
    driver.get(url)
    time.sleep(5)

    # بررسی اینکه آیا در صفحه صحیح هستیم
    current_url = driver.current_url
    logger.info(f"آدرس فعلی: {current_url}")

    if f"c={channel_id}" not in current_url:
        logger.info(f"❌ خطا در بارگذاری کانال {channel_id}")
        logger.info("تلاش مجدد...")
        driver.get(url)
        time.sleep(10)

        if f"c={channel_id}" not in driver.current_url:
            logger.info(f"❌❌ خطای جدی: نتوانستیم به کانال {channel_id} برویم. رد شدن از این کانال...")
            return False

    # پیدا کردن کانتینر پیام‌ها
    logger.info("🔍 در حال یافتن کانتینر اسکرول...")
    try:
        chat_container = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".scrollable.scrollable-y")))
        logger.info("✅ کانتینر اسکرول پیدا شد.")
    except TimeoutException:
        logger.error("❌ کانتینر اسکرول پیدا نشد.")
        return False

    # قرار دادن موس در موقعیت مناسب
    logger.info("\n⚠️ قرار دادن موس در وسط کانتینر...")
    try:
        first_message = chat_container.find_element(By.CSS_SELECTOR, "[data-msg-id]")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_message)
        time.sleep(2)
    except:
        logger.warning("⚠️ نتوانستم پیامی برای قرار دادن موس پیدا کنم، ادامه می‌دهم...")

    # شروع جمع‌آوری پیام‌ها
    seen_msg_ids = set()
    messages_data = []
    scroll_count = 0
    current_date = datetime.now().date()
    last_processed_date = None
    reached_last_post = False

    logger.info("🔄 شروع اسکرول به بالا برای بارگذاری پیام‌ها...")

    while not reached_last_post:
        scroll_count += 1
        logger.info(f"\n--- اسکرول شماره {scroll_count} ---")

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
                                logger.info(f"✅ به تاریخ آخرین پست ({last_post_date}) رسیدیم.")
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
                logger.info("⏳ اسکرول تغییری نکرد. بررسی نهایی...")
                time.sleep(3)

                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop - 100;", chat_container)
                time.sleep(2)

                current_scroll_top = driver.execute_script("return arguments[0].scrollTop;", chat_container)
                if current_scroll_top == prev_scroll_top:
                    logger.info("⏸️ به نظر می‌رسد به ابتدای تاریخچه رسیده‌ایم.")
                    break
            else:
                logger.info("🔍 پیام‌های جدید پیدا شد، ادامه اسکرول...")
        else:
            logger.info(f"📊 مجموع پیام‌های یکتا: {len(seen_msg_ids)}")

    # استخراج نهایی پیام‌ها
    logger.info("\n📥 در حال استخراج نازی پیام‌ها...")
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
            logger.error(f"❌ خطا در پردازش پیام: {str(e)}")
            continue

    # ارسال پست‌ها به API
    if messages_data:
        logger.info(f"\n📤 در حال ارسال پست‌های جدید به API...")
        if send_posts_to_api(messages_data, last_post_date):
            logger.info(f"✅ پست‌های جدید کانال {channel_name} با موفقیت ارسال شدند.")
            return True
        else:
            logger.error(f"❌ خطا در ارسال پست‌های کانال {channel_name}.")
            return False
    else:
        logger.info("ℹ️ هیچ پست جدیدی برای ارسال پیدا نشد.")
        return True


def run_crawler():
    """تابع اصلی اجرای کراولر"""
    global first_channel

    logger.info("🚀 شروع اجرای کراولر...")

    # راه‌اندازی درایور (فقط اگر وجود ندارد)
    if not setup_driver():
        return False

    # ورود دستی (فقط یک بار)
    if not is_logged_in and not manual_login():
        return False

    # لاگین به API
    if not login_to_api():
        return False

    # دریافت کانال‌ها
    channels = get_channels()
    if not channels:
        return False

    # پردازش هر کانال
    success_count = 0

    for channel in channels:
        try:
            if process_channel(channel):
                success_count += 1
        except Exception as e:
            logger.error(f"❌ خطا در پردازش کانال {channel.get('name')}: {str(e)}")
            logger.error(traceback.format_exc())

    logger.info(f"🔚 اجرای کراولر کامل شد. {success_count} از {len(channels)} کانال پردازش شدند.")
    return success_count > 0


def cleanup():
    """تمیزکاری هنگام خروج"""
    global driver
    if driver:
        try:
            driver.quit()
            logger.info("✅ مرورگر بسته شد.")
        except:
            pass


if __name__ == "__main__":
    try:
        # اولین اجرا را فوری انجام بده
        run_crawler()

        # برنامه‌ریزی برای اجرای بعدی هر 3 ساعت
        schedule.every(3).hours.do(run_crawler)

        logger.info("⏰ برنامه به صورت خودکار هر 3 ساعت اجرا می‌شود...")

        while True:
            schedule.run_pending()
            time.sleep(60)  # هر دقیقه چک می‌کند

    except KeyboardInterrupt:
        logger.info("⏹️ دریافت سیگنال توقف...")
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        cleanup()