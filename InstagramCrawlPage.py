import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv
import os
import schedule
import time
import logging

# تنظیمات لاگ‌گیری
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("instagram_crawler.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv(dotenv_path=".env")
# تنظیمات API
BASE_API_URL = os.getenv("BASE_API_URL_TMP")
LOGIN_URL = f"{BASE_API_URL}/token/"
CHANNEL_API_URL = f"{BASE_API_URL}/rep/channel-code/?platform=5"
POSTS_API_URL = f"{BASE_API_URL}/rep/posts/?platform=5&channel={{id}}"
POST_API_URL = f"{BASE_API_URL}/rep/posts/"

# اطلاعات لاگین
LOGIN_CREDENTIALS = {
    "username": os.getenv("API_USERNAME"),
    "password": os.getenv("API_PASSWORD")
}

# متغیرهای جهانی برای مدیریت توکن
access_token = None
token_expiration = None


def login_to_api():
    """ورود به سیستم و دریافت توکن دسترسی"""
    global access_token, token_expiration

    try:
        response = requests.post(LOGIN_URL, data=LOGIN_CREDENTIALS)
        response.raise_for_status()

        data = response.json()
        access_token = data.get('access')
        if access_token:
            # تنظیم زمان انقضا (فرض می‌کنیم توکن 1 ساعت معتبر است)
            token_expiration = datetime.now() + timedelta(minutes=55)
            logger.info("✅ ورود به API با موفقیت انجام شد.")
            return True
        else:
            logger.error("❌ خطا در دریافت توکن دسترسی.")
            return False
    except Exception as e:
        logger.error(f"❌ خطا در ورود به سیستم: {str(e)}")
        return False


def get_auth_headers():
    """تهیه هدرهای احراز هویت با بررسی انقضای توکن"""
    global access_token, token_expiration

    if not access_token or (token_expiration and datetime.now() >= token_expiration):
        logger.info("🔄 توکن منقضی شده یا وجود ندارد. در حال ورود مجدد...")
        if not login_to_api():
            raise Exception("عدم توانایی در ورود به سیستم")

    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }


def make_authenticated_request(method, url, max_retries=2, **kwargs):
    """
    انجام درخواست با احراز هویت و تلاش مجدد در صورت خطای احراز هویت
    """
    for attempt in range(max_retries):
        try:
            headers = get_auth_headers()
            if 'headers' in kwargs:
                kwargs['headers'].update(headers)
            else:
                kwargs['headers'] = headers

            response = requests.request(method, url, **kwargs)

            # اگر توکن منقضی شده باشد (کد 401)، لاگین مجدد و تلاش دوباره
            if response.status_code == 401 and attempt < max_retries - 1:
                logger.info("🔄 توکن منقضی شده. در حال لاگین مجدد و تلاش دوباره...")
                global access_token, token_expiration
                access_token = None
                token_expiration = None
                continue

            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 and attempt < max_retries - 1:
                logger.info("🔄 توکن منقضی شده. در حال لاگین مجدد و تلاش دوباره...")
                access_token = None
                token_expiration = None
                continue
            else:
                raise e
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            logger.warning(f"⚠️ خطا در درخواست (تلاش {attempt + 1}/{max_retries}): {str(e)}")
            time.sleep(1)  # تأثیر کمی قبل از تلاش مجدد


def convert_stats_to_number(stat_str):
    """
    تبدیل مقادیر لایک و کامنت از فرمت‌های مانند 1.5k, 1.5m به عدد
    """
    if not stat_str or stat_str == 'N/A':
        return 0

    stat_str = str(stat_str).lower().strip()
    if 'k' in stat_str:
        return int(float(stat_str.replace('k', '')) * 1000)
    elif 'm' in stat_str:
        return int(float(stat_str.replace('m', '')) * 1000000)
    else:
        try:
            return int(stat_str)
        except:
            return 0


def parse_time_ago(time_ago_str):
    """تبدیل رشته time_ago به تاریخ واقعی"""
    if not time_ago_str or time_ago_str == 'N/A':
        return None

    now = datetime.now()
    time_ago_str = str(time_ago_str).lower()

    if 'just now' in time_ago_str:
        return now

    parts = time_ago_str.split()
    if len(parts) < 2:
        return None

    try:
        num = int(parts[0])
    except ValueError:
        return None

    unit = parts[1].lower()

    if 'second' in unit:
        delta = timedelta(seconds=num)
    elif 'minute' in unit:
        delta = timedelta(minutes=num)
    elif 'hour' in unit:
        delta = timedelta(hours=num)
    elif 'day' in unit:
        delta = timedelta(days=num)
    elif 'week' in unit:
        delta = timedelta(weeks=num)
    elif 'month' in unit:
        delta = timedelta(days=num * 30)
    elif 'year' in unit:
        delta = timedelta(days=num * 365)
    else:
        return None

    return now - delta


def extract_hashtags(text):
    """استخراج هشتگ‌ها از متن پست"""
    if not text or text == 'N/A':
        return " "

    hashtags = re.findall(r'#(\w+)', text)
    if not hashtags:
        return " "

    formatted_hashtags = " ".join(f"#{tag}" for tag in hashtags)
    return formatted_hashtags


def extract_mentions(text):
    """استخراج منشن‌ها از متن پست"""
    if not text or text == 'N/A':
        return []
    return re.findall(r'@(\w+)', text)


def get_post_details(post_url):
    """استخراج جزئیات پست از صفحه اختصاصی آن"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(post_url, headers=headers, timeout=30)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        post_card = soup.find('div', class_='card sm:w-1/2 mx-2 sm:mx-auto bg-base-100 shadow-xl relative dark:bg-slate-900')

        if not post_card:
            return None

        # تشخیص نوع محتوا
        content_type = "text"
        if post_card.find('video'):
            content_type = "video"
        elif post_card.find('img'):
            content_type = "image"
        elif post_card.find('div', id='cardcarousel'):
            content_type = "slideshow"

        # استخراج آمار
        def extract_stat(icon_class, convert_to_number=False):
            element = post_card.find('span', class_=icon_class)
            if element and element.parent:
                stat_text = element.parent.get_text(strip=True).replace(icon_class, '').strip()
                if convert_to_number:
                    return convert_stats_to_number(stat_text)
                return stat_text
            return '0' if convert_to_number else 'N/A'

        time_ago_str = extract_stat('hero-clock')
        actual_post_time = parse_time_ago(time_ago_str) if time_ago_str != 'N/A' else None

        stats = {
            'likes': extract_stat('hero-hand-thumb-up', convert_to_number=True),
            'comments': extract_stat('hero-chat-bubble-left-right', convert_to_number=True),
            'time_ago': time_ago_str,
            'actual_post_time': actual_post_time.strftime('%Y-%m-%d %H:%M:%S') if actual_post_time else 'N/A'
        }

        return {
            'content_type': content_type,
            'likes': stats['likes'],
            'comments': stats['comments'],
            'time_ago': stats['time_ago'],
            'actual_post_time': stats['actual_post_time']
        }
    except Exception as e:
        logger.error(f"❌ خطا در دریافت جزئیات پست {post_url}: {str(e)}")
        return None


def get_channel_posts(channel_id, channel_name):
    """دریافت پست‌های یک کانال و پردازش آنها"""
    url = POSTS_API_URL.format(id=channel_id)

    try:
        print("******************")
        response = make_authenticated_request('GET', url, timeout=30)
        print("++++++++++++++++++")
        existing_posts = response.json()
        existing_message_ids = {str(post['message_id'])[-7:] for post in existing_posts}
    except Exception as e:
        logger.error(f"❌ خطا در دریافت پست‌های موجود برای کانال {channel_id}: {str(e)}")
        existing_message_ids = set()

    # دریافت پست‌ها از dumpor.io
    main_url = f"https://dumpor.io/v/{channel_name}"
    headers_dumpor = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(main_url, headers=headers_dumpor, timeout=30)
        if response.status_code != 200:
            logger.error(f"❌ خطا در دریافت صفحه کانال {channel_name}: کد وضعیت {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        post_cards = soup.find_all('div',
                                   class_='group overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900',
                                   limit=20)

        messages_data = []

        for card in post_cards:
            try:
                # استخراج اطلاعات پایه
                post_link_element = card.find('a')
                post_link = "https://dumpor.io" + post_link_element['href'] if post_link_element else 'N/A'

                image_element = card.find('img')
                image_url = image_element['src'] if image_element else 'N/A'

                title = image_element['alt'] if image_element and image_element.get('alt') else 'N/A'

                # استخراج متن پست - استفاده از کلاس صحیح
                card_body = card.find('p', class_='text-sm leading-6 text-slate-800 dark:text-slate-100 line-clamp-3')
                post_text = card_body.get_text(strip=True) if card_body else 'N/A'

                # استخراج جزئیات بیشتر از صفحه پست
                post_details = get_post_details(post_link) if post_link != 'N/A' else None

                # استخراج message_id از لینک
                msg_id = post_link.split('/c/')[-1] if '/c/' in post_link else None
                if not msg_id:
                    continue

                # حذف کاراکترهای غیرعددی و گرفتن 7 رقم آخر
                msg_id = ''.join(filter(str.isdigit, msg_id))[-7:]
                if not msg_id:
                    continue

                # اگر پست قبلاً وجود دارد، از پردازش صرف‌نظر می‌کنیم
                if msg_id in existing_message_ids:
                    continue

                # استخراج هشتگ‌ها و منشن‌ها
                hashtags = extract_hashtags(post_text)
                mentions = extract_mentions(post_text)

                # ترکیب entities
                entities = []
                if image_url and image_url != 'N/A':
                    entities.append(image_url)
                entities.extend(mentions)

                # محاسبه views بر اساس نوع محتوا
                likes = convert_stats_to_number(post_details['likes']) if post_details else 0

                # اگر محتوا ویدیو است: views = likes * 20
                # اگر محتوا عکس است: views = 0
                if post_details and post_details['content_type'] == 'video':
                    views = likes * 20
                else:
                    views = 0

                # تاریخ پست
                if post_details and post_details['actual_post_time'] != 'N/A':
                    try:
                        post_time = datetime.strptime(post_details['actual_post_time'], '%Y-%m-%d %H:%M:%S')
                    except:
                        post_time = datetime.now()
                else:
                    post_time = datetime.now()

                # آماده‌سازی داده برای ارسال
                messages_data.append({
                    "message_id": msg_id,
                    "date": post_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "post_text": post_text,
                    "hashtags": hashtags,
                    "views": views,
                    "chat_type": "channel",
                    "has_media": True,
                    "collected_at": post_time.strftime('%Y-%m-%d'),
                    "author": 1,
                    "channel": channel_id,
                    "Entities": ",".join(entities),
                    "likes": likes,
                    "comments": convert_stats_to_number(post_details['comments']) if post_details else 0
                })

            except Exception as e:
                logger.error(f"❌ خطا در پردازش کارت پست: {str(e)}")
                continue

        return messages_data

    except Exception as e:
        logger.error(f"❌ خطا در پردازش پست‌های کانال {channel_name}: {str(e)}")
        return []


def send_posts_to_api(posts_data):
    """ارسال پست‌های جدید به API"""
    if not posts_data:
        return True

    success_count = 0

    try:
        for post in posts_data:
            try:
                # حذف فیلدهای موقتی
                post_to_send = post.copy()
                # post_to_send.pop('likes', None)
                # post_to_send.pop('comments', None)

                response = make_authenticated_request('POST', POST_API_URL, json=post_to_send, timeout=30)
                response.raise_for_status()
                success_count += 1
                logger.info(f"✅ پست با شناسه {post['message_id']} با موفقیت ارسال شد.")
            except Exception as e:
                logger.error(f"❌ خطا در ارسال پست {post.get('message_id', 'unknown')}: {str(e)}")
                continue

        logger.info(f"✅ {success_count} از {len(posts_data)} پست با موفقیت ارسال شدند.")
        return success_count > 0
    except Exception as e:
        logger.error(f"❌ خطا در ارسال پست‌ها به API: {str(e)}")
        return False


def run_crawler():
    """تابع اصلی اجرای کراولر"""
    logger.info("🚀 شروع اجرای کراولر اینستاگرام...")

    # ورود به سیستم
    if not login_to_api():
        logger.error("❌ عدم توانایی در ورود به سیستم.")
        return False

    # دریافت لیست کانال‌ها
    try:
        response = make_authenticated_request('GET', CHANNEL_API_URL, timeout=30)
        channels = response.json()
        logger.info(f"📊 تعداد {len(channels)} کانال برای پردازش دریافت شد.")
    except Exception as e:
        logger.error(f"❌ خطا در دریافت لیست کانال‌ها: {str(e)}")
        return False

    total_posts_processed = 0
    successful_channels = 0

    # پردازش هر کانال
    for channel in channels:
        channel_id = channel.get('id')
        channel_code = channel.get('channel_id')

        if not channel_id or not channel_code:
            continue

        logger.info(f"\n🔍 در حال پردازش کانال {channel_code} (شناسه: {channel_id})...")

        # دریافت و پردازش پست‌های کانال
        posts_data = get_channel_posts(channel_id, channel_code)

        if posts_data:
            logger.info(f"📥 تعداد {len(posts_data)} پست جدید برای کانال {channel_code} یافت شد.")

            # ارسال پست‌های جدید به API
            if send_posts_to_api(posts_data):
                logger.info(f"✅ پست‌های کانال {channel_code} با موفقیت ارسال شدند.")
                successful_channels += 1
                total_posts_processed += len(posts_data)
            else:
                logger.error(f"❌ خطا در ارسال پست‌های کانال {channel_code}.")
        else:
            logger.info(f"ℹ️ هیچ پست جدیدی برای کانال {channel_code} یافت نشد.")
            successful_channels += 1  # حتی اگر پستی نبود، کانال موفق در نظر گرفته می‌شود

    logger.info(
        f"\n🎉 اجرای کامل شد. {successful_channels}/{len(channels)} کانال پردازش شدند. {total_posts_processed} پست جدید ارسال شد.")
    return successful_channels > 0


def main():
    """تابع اصلی با قابلیت اجرای دوره‌ای"""
    try:
        # اولین اجرا
        run_crawler()

        # برنامه‌ریزی برای اجرای هر 6 ساعت
        schedule.every(6).hours.do(run_crawler)

        logger.info("⏰ برنامه به صورت خودکار هر 6 ساعت اجرا خواهد شد...")

        # حلقه اصلی برای اجرای دوره‌ای
        while True:
            schedule.run_pending()
            time.sleep(60)  # هر دقیقه چک کند

    except KeyboardInterrupt:
        logger.info("⏹️ دریافت سیگنال توقف...")
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره: {str(e)}")


if __name__ == "__main__":
    # نصب کتابخانه مورد نیاز اگر وجود ندارد
    try:
        import schedule
    except ImportError:
        print("📦 در حال نصب کتابخانه schedule...")
        import subprocess

        subprocess.check_call(["pip", "install", "schedule"])
        import schedule

    main()