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

# ——— تنظیمات تلگرام ———
api_id = 27873457
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

# ——— کلاینت تلگرام مشترک ———
client = None


# ——— توابع کمکی ———
def setup_proxy():
    socks.set_default_proxy(
        proxy_type=socks.SOCKS5,
        addr=os.getenv("PRX_ADDR"),
        port=9443,
        username=os.getenv("PRX_USERNAME"),
        password=os.getenv("PRX_PASSWORD")
    )
    socket.socket = socks.socksocket


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
                    # اضافه کردن اطلاعات document برای عکس
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


# ——— توابع API ———
def login():
    global access_token
    try:
        response = requests.post(LOGIN_URL, data={
            'username': API_USERNAME,
            'password': API_PASSWORD
        })
        if response.status_code == 200:
            access_token = response.json().get('access')
            return True
        print(f"❌ خطا در ورود: {response.text}")
        return False
    except Exception as e:
        print(f"❌ خطا در ارتباط با سرور: {e}")
        return False


def get_headers():
    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }


def get_channels():
    try:
        response = requests.get(CHANNEL_API_URL, headers=get_headers())
        if response.status_code == 401:  # توکن منقضی شده
            if login():
                return get_channels()
            return []
        if response.status_code == 200:
            return response.json()
        print(f"❌ خطا در دریافت لیست کانال‌ها: {response.text}")
        return []
    except Exception as e:
        print(f"❌ خطا در ارتباط با سرور: {e}")
        return []


def get_last_message_id(channel_id):
    try:
        # url = f"http://10.32.141.78:8081/api/sapi/rep/posts/?platform=3&channel={channel_id}"
        url = f"http://10.32.213.16:8000/sapi/rep/posts/?platform=3&channel={channel_id}"
        response = requests.get(url, headers=get_headers())
        if response.status_code == 401:  # توکن منقضی شده
            if login():
                return get_last_message_id(channel_id)
            return None
        if response.status_code == 200:
            posts = response.json()
            if posts and len(posts) > 0:
                return max(post['message_id'] for post in posts)
        return None
    except Exception as e:
        print(f"❌ خطا در دریافت آخرین message_id: {e}")
        return None


def send_post_to_api(post_data):
    try:
        post_data['author'] = 1  # تنظیم author به 1
        response = requests.post(
            POSTS_API_URL,
            data=json.dumps(post_data),
            headers=get_headers()
        )
        if response.status_code == 401:  # توکن منقضی شده
            if login():
                return send_post_to_api(post_data)
            return False
        if response.status_code in [200, 201]:
            return True
        print("*********************************************")
        print(post_data)
        print("**********************************************")
        print(f"❌ خطا در ارسال پست: {response.text}")
        print("**********************************************")
        return False
    except Exception as e:
        print(f"❌ خطا در ارسال پست به API: {e}")
        return False


# ——— تابع اصلی کرال ———
async def scrape_channel(channel_username, channel_id):
    global client

    print(f"\n🔍 شروع کرال کانال: {channel_username} (ID: {channel_id})")

    try:
        # دریافت آخرین message_id از API
        last_message_id = get_last_message_id(channel_id)
        print(f"آخرین message_id ذخیره شده: {last_message_id if last_message_id is not None else 'بدون سابقه'}")

        # دریافت پیام‌ها از تلگرام
        messages = await get_telegram_messages(client, channel_username, last_message_id)

        if not messages:
            print("⚠️ هیچ پیام جدیدی یافت نشد")
            return 0

        # پردازش و ارسال پیام‌ها
        success_count = 0
        for message in messages:
            if process_and_send_message(message, channel_id):
                success_count += 1

        print(f"\n✅ کرال کانال {channel_username} کامل شد")
        print(f"تعداد پست‌های جدید ارسال شده: {success_count}/{len(messages)}")
        return success_count

    except Exception as e:
        print(f"\n❌ خطا در کرال کانال {channel_username}: {str(e)}")
        return 0


async def get_telegram_messages(client, channel_username, last_message_id=None):
    """دریافت پیام‌ها از تلگرام با فیلتر پیام‌های جدید"""
    try:
        # دریافت 100 پیام آخر
        messages = await client.get_messages(
            channel_username,
            limit=100
        )

        # اگر last_message_id وجود داشت، فقط پیام‌های جدیدتر را فیلتر کن
        if last_message_id is not None:
            messages = [m for m in messages if m.id > last_message_id]

        return messages

    except Exception as e:
        print(f"خطا در دریافت پیام‌ها: {str(e)}")
        return []


def process_and_send_message(message, channel_id):
    """پردازش یک پیام و ارسال به API"""
    try:
        # تبدیل تاریخ به فرمت مورد نظر
        post_date = format_tehran_datetime(message.date)

        # استخراج متن و هشتگ‌ها
        text = message.text or getattr(message, 'message', '') or (
            getattr(message.media, 'caption', '') if message.media else '')
        hashtags = ' '.join(extract_hashtags(text)) if text else ''

        # دریافت اطلاعات چت
        chat = message.chat if message.chat else message.sender
        chat_info = {
            'chat_id': str(chat.id),
            'chat_type': str(type(chat).__name__),
            'chat_title': getattr(chat, 'title', None),
            'chat_username': getattr(chat, 'username', None)
        }

        # دریافت اطلاعات فرستنده
        sender_info = get_sender_info(message.sender if message.sender else message.from_id)

        # ساخت دیکشنری پست
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

        # ارسال به API
        return send_post_to_api(post_data)

    except Exception as e:
        print(f"خطا در پردازش پیام {message.id if message else 'N/A'}: {str(e)}")
        return False


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
    global client

    # ورود به سیستم
    print("**************")
    if not login():
        print("❌ امکان ورود به سیستم وجود ندارد")
        return

    # ایجاد کلاینت تلگرام مشترک
    # setup_proxy()  # اگر نیاز به پراکسی دارید، این خط را فعال کنید
    client = TelegramClient('session_shared', api_id, api_hash)
    await client.start(phone)
    print("✅ کلاینت تلگرام راه‌اندازی شد")
    time.sleep(10)

    # دریافت لیست کانال‌ها
    channels = get_channels()
    if not channels:
        print("❌ هیچ کانالی یافت نشد")
        await client.disconnect()
        return

    print(f"🔍 تعداد کانال‌ها برای کرال: {len(channels)}")

    # کرال هر کانال
    for channel in channels:
        print(f"\n📡 شروع کرال کانال: {channel['name']} ({channel['channel_id']})")
        await scrape_channel(channel['channel_id'], channel['id'])
        time.sleep(10)  # تاخیر بین کرال کانال‌های مختلف

    # قطع اتصال از تلگرام
    await client.disconnect()
    print("✅ تمام کانال‌ها با موفقیت کرال شدند")


if __name__ == '__main__':
    asyncio.run(main())