import time
import requests
from telethon import TelegramClient, functions, types
import asyncio
import socks
import socket
from datetime import datetime
import pytz
import json
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")

# ——— تنظیمات API ———
BASE_URL = os.getenv("BASE_API_URL")
LOGIN_URL = f"{BASE_URL}/token/"
CHANNEL_API_URL = f"{BASE_URL}/rep/channel-code/?platform=3"
POSTS_API_URL = f"{BASE_URL}/rep/posts/"

# ——— تنظیمات احراز هویت ———
API_USERNAME = os.getenv("API_USERNAME")
API_PASSWORD = os.getenv("API_PASSWORD")
access_token = None
token_expiry_time = None

# ——— تنظیمات تلگرام ———
api_id = 27873457
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

# ——— کلاینت تلگرام مشترک ———
client = None

# ——— ذخیره‌سازی موقت پست‌ها ———
collected_posts = []


# ——— توابع کمکی ———
def setup_proxy(enable=True):
    """فعال یا غیرفعال کردن پراکسی"""
    if enable:
        socks.set_default_proxy(
            proxy_type=socks.SOCKS5,
            addr=os.getenv("PRX_ADDR"),
            port=9443,
            username=os.getenv("PRX_USERNAME"),
            password=os.getenv("PRX_PASSWORD")
        )
        socket.socket = socks.socksocket
        print("✅ پراکسی فعال شد")
    else:
        socks.set_default_proxy()
        socket.socket = socket._socketobject
        print("✅ پراکسی غیرفعال شد")


def wait_for_user(message):
    """منتظر ماندن برای تأیید کاربر"""
    print(f"\n📢 {message}")
    input("پس از انجام کار، Enter را بفشارید...")


def extract_hashtags(text):
    return [word for word in text.split() if word.startswith('#')] if text else []


def format_tehran_datetime(dt):
    tehran_tz = pytz.timezone('Asia/Tehran')
    tehran_time = dt.astimezone(tehran_tz)
    return tehran_time.strftime('%Y-%m-%dT%H:%M:%S+03:30')


def format_tehran_date(dt):
    tehran_tz = pytz.timezone('Asia/Tehran')
    tehran_time = dt.astimezone(tehran_tz)
    return tehran_time.strftime('%Y-%m-%d')


def get_photo_size(photo_size):
    if isinstance(photo_size, types.PhotoSizeProgressive):
        return photo_size.sizes[-1] if photo_size.sizes else 0
    return getattr(photo_size, 'size', 0)


def get_media_info(message):
    media_info = {
        'has_media': False,
        'photo_file_id': None,
        'photo_file_unique_id': None,
        'photo_width': None,
        'photo_height': None,
        'photo_file_size': None,
        'video_file_id': None,
        'video_file_unique_id': None,
        'video_width': None,
        'video_height': None,
        'video_duration': 0,
        'video_file_size': None,
        'document_file_id': None,
        'document_file_unique_id': None,
        'document_file_name': None,
        'document_mime_type': None,
        'document_file_size': None
    }

    if message.media:
        media_info['has_media'] = True
        if isinstance(message.media, types.MessageMediaPhoto):
            photo = message.media.photo
            if photo:
                largest_size = max(photo.sizes, key=lambda s: get_photo_size(s)) if photo.sizes else None
                media_info.update({
                    'photo_file_id': photo.id,
                    'photo_file_unique_id': photo.access_hash,
                    'photo_width': largest_size.w if largest_size else None,
                    'photo_height': largest_size.h if largest_size else None,
                    'photo_file_size': get_photo_size(largest_size) if largest_size else None,
                    'document_file_id': photo.id,
                    'document_file_unique_id': photo.access_hash,
                    'document_file_name': f"photo_{photo.id}.jpg",
                    'document_mime_type': 'image/jpeg',
                    'document_file_size': get_photo_size(largest_size) if largest_size else None
                })
        elif isinstance(message.media, types.MessageMediaDocument):
            doc = message.media.document
            if doc:
                media_info.update({
                    'document_file_id': doc.id,
                    'document_file_unique_id': doc.access_hash,
                    'document_file_name': next((attr.file_name for attr in doc.attributes if
                                                isinstance(attr, types.DocumentAttributeFilename)), None),
                    'document_mime_type': doc.mime_type,
                    'document_file_size': doc.size
                })
                video_attr = next((attr for attr in doc.attributes if isinstance(attr, types.DocumentAttributeVideo)),
                                  None)
                if video_attr:
                    media_info.update({
                        'video_file_id': doc.id,
                        'video_file_unique_id': doc.access_hash,
                        'video_width': video_attr.w,
                        'video_height': video_attr.h,
                        'video_duration': 0,
                        'video_file_size': doc.size
                    })
    return media_info


def get_forward_info(message):
    forward_info = {
        'forward_from_id': None,
        'forward_from_name': None,
        'forward_from_username': None,
        'forward_date': None,
        'forward_from_chat_id': None,
        'forward_from_chat_title': None,
        'forward_from_chat_username': None,
        'forward_from_message_id': None,
        'forward_origin_type': None,
        'forward_origin_sender_id': None,
        'forward_origin_sender_name': None
    }

    if message.fwd_from:
        forward_info['forward_date'] = format_tehran_datetime(message.fwd_from.date) if message.fwd_from.date else None
        forward_info['forward_from_message_id'] = message.fwd_from.channel_post if hasattr(message.fwd_from,
                                                                                           'channel_post') else None

        if hasattr(message.fwd_from, 'from_id'):
            if isinstance(message.fwd_from.from_id, types.PeerUser):
                forward_info['forward_from_id'] = message.fwd_from.from_id.user_id
            elif isinstance(message.fwd_from.from_id, types.PeerChannel):
                forward_info['forward_from_chat_id'] = message.fwd_from.from_id.channel_id

        if hasattr(message.fwd_from, 'from_name'):
            forward_info['forward_from_name'] = message.fwd_from.from_name

        if hasattr(message.fwd_from, 'channel_id'):
            forward_info['forward_from_chat_id'] = message.fwd_from.channel_id

        if hasattr(message.fwd_from, 'post_author'):
            forward_info['forward_from_name'] = message.fwd_from.post_author

    return forward_info


def get_reply_info(message):
    return {
        'reply_to_message_id': message.reply_to_msg_id if message.reply_to_msg_id else None
    }


# ——— توابع مدیریت توکن ———
def login():
    """ورود به سیستم و دریافت توکن"""
    global access_token, token_expiry_time

    try:
        response = requests.post(LOGIN_URL, data={
            'username': API_USERNAME,
            'password': API_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access')

            # محاسبه زمان انقضای توکن (معمولاً 60 دقیقه)
            token_expiry_time = datetime.now() + timedelta(minutes=55)  # 5 دقیقه زودتر renew کنیم

            print("✅ ورود به سیستم موفق")
            return True
        print(f"❌ خطا در ورود: {response.text}")
        return False
    except Exception as e:
        print(f"❌ خطا در ارتباط با سرور: {e}")
        return False


def is_token_valid():
    """بررسی معتبر بودن توکن"""
    global token_expiry_time

    if not access_token or not token_expiry_time:
        return False

    return datetime.now() < token_expiry_time


def ensure_valid_token():
    """اطمینان از معتبر بودن توکن"""
    if not is_token_valid():
        print("🔄 توکن منقضی شده، در حال دریافت توکن جدید...")
        return login()
    return True


def get_headers():
    """دریافت هدرها با توکن معتبر"""
    if not ensure_valid_token():
        raise Exception("عدم امکان دریافت توکن معتبر")

    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }


def make_authenticated_request(request_func, *args, **kwargs):
    """انجام درخواست با مدیریت خودکار توکن"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # اطمینان از معتبر بودن توکن قبل از هر درخواست
            ensure_valid_token()

            # اضافه کردن هدرها به kwargs
            if 'headers' not in kwargs:
                kwargs['headers'] = get_headers()
            else:
                kwargs['headers']['Authorization'] = f'Bearer {access_token}'

            response = request_func(*args, **kwargs)

            # اگر توکن منقضی شده، دوباره امتحان کن
            if response.status_code == 401:
                print(f"🔄 توکن منقضی شده، تلاش مجدد {attempt + 1}/{max_retries}...")
                login()  # دریافت توکن جدید
                continue

            return response

        except Exception as e:
            print(f"❌ خطا در درخواست (تلاش {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise e
            time.sleep(2)  # تاخیر قبل از تلاش مجدد

    return None


# ——— توابع API ———
def get_channels_with_last_post():
    """دریافت کانال‌ها به همراه آخرین پست هر کانال"""
    try:
        response = make_authenticated_request(requests.get, CHANNEL_API_URL)
        if response and response.status_code == 200:
            channels = response.json()

            # دریافت آخرین پست هر کانال
            for channel in channels:
                channel_id = channel['id']
                last_post = get_last_post_for_channel(channel_id)
                channel['last_post_id'] = last_post
                channel['last_post_date'] = get_last_post_date_for_channel(channel_id)

            return channels
        print(f"❌ خطا در دریافت لیست کانال‌ها")
        return []
    except Exception as e:
        print(f"❌ خطا در ارتباط با سرور: {e}")
        return []


def get_last_post_for_channel(channel_id):
    """دریافت آخرین message_id برای یک کانال خاص"""
    try:
        url = f"{BASE_URL}/rep/posts/?platform=3&channel={channel_id}"
        response = make_authenticated_request(requests.get, url)
        if response and response.status_code == 200:
            posts = response.json()
            if posts and len(posts) > 0:
                return max(post['message_id'] for post in posts)
        return None
    except Exception as e:
        print(f"⚠️ خطا در دریافت آخرین پست برای کانال {channel_id}: {e}")
        return None


def get_last_post_date_for_channel(channel_id):
    """دریافت تاریخ آخرین پست برای یک کانال خاص"""
    try:
        url = f"{BASE_URL}/rep/posts/?platform=3&channel={channel_id}"
        response = make_authenticated_request(requests.get, url)
        if response and response.status_code == 200:
            posts = response.json()
            if posts and len(posts) > 0:
                latest_post = max(posts, key=lambda x: x['message_id'])
                return latest_post.get('date', 'نامشخص')
        return 'بدون سابقه'
    except Exception as e:
        print(f"⚠️ خطا در دریافت تاریخ آخرین پست: {e}")
        return 'خطا'


def send_all_posts_to_api():
    """ارسال همه پست‌های جمع‌آوری شده به API"""
    global collected_posts

    if not collected_posts:
        print("⚠️ هیچ پستی برای ارسال وجود ندارد")
        return True

    print(f"\n📤 شروع ارسال {len(collected_posts)} پست به API...")

    success_count = 0
    failed_count = 0

    for i, post_data in enumerate(collected_posts, 1):
        try:
            # استفاده از درخواست authenticated
            response = make_authenticated_request(
                requests.post,
                POSTS_API_URL,
                data=json.dumps({**post_data, 'author': 1}),
                timeout=30
            )

            if response and response.status_code in [200, 201]:
                success_count += 1
                print(f"✅ پست {i}/{len(collected_posts)} ارسال شد")
            else:
                failed_count += 1
                error_msg = response.text if response else "بدون پاسخ"
                print(f"❌ خطا در ارسال پست {i}: {error_msg}")

        except Exception as e:
            failed_count += 1
            print(f"❌ خطا در ارسال پست {i}: {e}")

        # تاخیر بین ارسال پست‌ها برای جلوگیری از overload
        time.sleep(1)

    print(f"\n📊 نتایج ارسال:")
    print(f"• موفق: {success_count}")
    print(f"• ناموفق: {failed_count}")
    print(f"• کل: {len(collected_posts)}")

    return failed_count == 0


# ——— تابع اصلی کرال ———
async def scrape_channel(channel_username, channel_id, last_post_id=None):
    global client, collected_posts

    print(f"\n🔍 شروع کرال کانال: {channel_username}")

    try:
        messages = await get_telegram_messages(client, channel_username, last_post_id)

        if not messages:
            print("⚠️ هیچ پیام جدیدی یافت نشد")
            return 0

        # پردازش و ذخیره پیام‌ها (بدون ارسال به API)
        success_count = 0
        for message in messages:
            post_data = process_message(message, channel_id)
            if post_data:
                collected_posts.append(post_data)
                success_count += 1

        print(f"✅ کرال کانال {channel_username} کامل شد")
        print(f"📥 پست‌های جمع‌آوری شده: {success_count}/{len(messages)}")
        return success_count

    except Exception as e:
        print(f"❌ خطا در کرال کانال {channel_username}: {str(e)}")
        return 0


async def get_telegram_messages(client, channel_username, last_message_id=None):
    """دریافت پیام‌ها از تلگرام با فیلتر پیام‌های جدید"""
    try:
        messages = await client.get_messages(channel_username, limit=100)

        if last_message_id is not None:
            messages = [m for m in messages if m.id > last_message_id]

        return messages[::-1]  # بازگرداندن به ترتیب قدیم به جدید

    except Exception as e:
        print(f"❌ خطا در دریافت پیام‌ها: {str(e)}")
        return []


def process_message(message, channel_id):
    """پردازش یک پیام و بازگرداندن دیکشنری داده"""
    try:
        post_date = format_tehran_datetime(message.date)

        text = message.text or getattr(message, 'message', '') or (
            getattr(message.media, 'caption', '') if message.media else '')
        hashtags = ' '.join(extract_hashtags(text)) if text else ''

        chat = message.chat if message.chat else message.sender
        chat_info = {
            'chat_id': str(chat.id),
            'chat_type': str(type(chat).__name__),
            'chat_title': getattr(chat, 'title', None),
            'chat_username': getattr(chat, 'username', None)
        }

        sender_info = get_sender_info(message.sender if message.sender else message.from_id)

        post_data = {
            'channel': channel_id,
            'post_text': text,
            'hashtags': hashtags,
            'message_id': message.id,
            'date': post_date,
            **chat_info,
            **sender_info,
            **get_media_info(message),
            **get_forward_info(message),
            **get_reply_info(message),
            'views': message.views if hasattr(message, 'views') else 0,
            'collected_at': format_tehran_date(message.date),
            'author': 1,
            'entities': str(message.entities) if message.entities else '[]'
        }

        return post_data

    except Exception as e:
        print(f"❌ خطا در پردازش پیام {message.id}: {str(e)}")
        return None


def get_sender_info(sender):
    """استخراج اطلاعات فرستنده"""
    if not sender:
        return {
            'sender_id': None,
            'sender_is_bot': False,
            'sender_name': None,
            'sender_username': None
        }

    return {
        'sender_id': sender.id,
        'sender_is_bot': getattr(sender, 'bot', False),
        'sender_name': f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip(),
        'sender_username': getattr(sender, 'username', None)
    }


async def main():
    global client, collected_posts

    print("=" * 50)
    print("🔄 شروع فرآیند کرال تلگرام")
    print("=" * 50)

    # مرحله 1: دریافت اطلاعات از API (بدون پراکسی)
    print("\n📍 مرحله 1: دریافت اطلاعات از API")
    print("➡️ پراکسی باید خاموش باشد")

    if not login():
        print("❌ امکان ورود به سیستم وجود ندارد")
        return

    # دریافت کانال‌ها و آخرین پست‌ها
    channels = get_channels_with_last_post()
    if not channels:
        print("❌ هیچ کانالی یافت نشد")
        return

    print(f"✅ تعداد کانال‌ها: {len(channels)}")

    # نمایش اطلاعات کانال‌ها
    print("\n📋 اطلاعات کانال‌ها:")
    for i, channel in enumerate(channels, 1):
        print(f"{i}. {channel['name']} - آخرین پست: {channel['last_post_id'] or 'بدون سابقه'}")

    # مرحله 2: کرال از تلگرام (با پراکسی)
    print("\n📍 مرحله 2: کرال از تلگرام")
    wait_for_user("لطفاً پراکسی را روشن کنید")

    # فعال‌سازی پراکسی
    # setup_proxy(enable=True)

    # اتصال به تلگرام
    client = TelegramClient('session_shared', api_id, api_hash)
    await client.start(phone)
    print("✅ کلاینت تلگرام راه‌اندازی شد")
    time.sleep(3)

    # کرال هر کانال (فقط جمع‌آوری داده - بدون ارسال به API)
    total_results = {
        'total_channels': len(channels),
        'successful_channels': 0,
        'total_posts': 0,
        'start_time': datetime.now().isoformat()
    }

    for channel in channels:
        success_count = await scrape_channel(
            channel['channel_id'],
            channel['id'],
            channel['last_post_id']
        )

        if success_count > 0:
            total_results['successful_channels'] += 1
            total_results['total_posts'] += success_count

        time.sleep(3)  # تاخیر بین کانال‌ها

    total_results['end_time'] = datetime.now().isoformat()

    # قطع اتصال از تلگرام
    await client.disconnect()
    print("✅ کرال تلگرام کامل شد")

    # مرحله 3: ارسال داده‌ها به API (بدون پراکسی)
    print("\n📍 مرحله 3: ارسال داده‌ها به API")
    wait_for_user("لطفاً پراکسی را خاموش کنید")

    # غیرفعال‌سازی پراکسی
    # setup_proxy(enable=False)

    # ارسال همه پست‌ها به API با مدیریت توکن
    if collected_posts:
        send_all_posts_to_api()
    else:
        print("⚠️ هیچ داده‌ای برای ارسال وجود ندارد")

    # نمایش نتایج نهایی
    print("\n📊 نتایج نهایی کرال:")
    print("=" * 30)
    print(f"• تعداد کل کانال‌ها: {total_results['total_channels']}")
    print(f"• کانال‌های موفق: {total_results['successful_channels']}")
    print(f"• تعداد کل پست‌ها: {total_results['total_posts']}")
    print(f"• زمان شروع: {total_results['start_time']}")
    print(f"• زمان پایان: {total_results['end_time']}")
    print("=" * 30)
    print("\n🎉 فرآیند کرال با موفقیت به پایان رسید!")


if __name__ == '__main__':
    # اضافه کردن import لازم
    from datetime import timedelta

    asyncio.run(main())