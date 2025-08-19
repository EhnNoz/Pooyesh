import requests
import os
import json
import time
from datetime import datetime
import schedule
import logging
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
# --- تنظیمات API ---
BASE_API_URL = os.getenv("BASE_API_URL")
# --- تنظیمات لاگ‌گیری ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bale_bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# --- تنظیمات ---
BOT_TOKENS = [
    os.getenv("BOT_TOKEN_3")
    # اینجا می‌توانید توکن‌های دیگر را اضافه کنید
    # "توکن_ربات_جدید",
]

# --- API URLs ---
AUTHOR_API_URL = f"{BASE_API_URL}/rep/authors-update/"
CHANNEL_API_URL = f"{BASE_API_URL}/rep/channel-code/?platform=2"
POST_API_URL = f"{BASE_API_URL}/rep/posts/"
LOGIN_URL = f"{BASE_API_URL}/token/"

# --- فایل ذخیره پیام‌های دیده‌شده ---
SEEN_FILE = "seen_messages.json"

# --- بارگذاری پیام‌های دیده‌شده ---
def load_seen_messages():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            logging.error(f"خطا در بارگذاری seen_messages: {e}")
    return set()

def save_seen_messages():
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(SEEN_MESSAGES), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"خطا در ذخیره seen_messages: {e}")

# --- متغیرهای کمکی ---
SEEN_MESSAGES = load_seen_messages()

# --- توکن احراز هویت داخلی ---
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
        if response.status_code == 200:
            tokens = response.json()
            logging.info("ورود موفقیت‌آمیز به API.")
            return tokens['access']
        else:
            logging.error(f"خطا در ورود: {response.text}")
            return None
    except Exception as e:
        logging.error(f"خطا در اتصال به API ورود: {e}")
        return None

# --- 1️⃣ دریافت آپدیت‌ها از Bale ---
def get_all_updates(bot_base_url, offset: int = 0):
    params = {'offset': offset, 'timeout': 5}
    try:
        response = requests.get(f"{bot_base_url}/getUpdates", params=params)
        response.raise_for_status()
        return response.json().get('result', [])
    except requests.exceptions.RequestException as e:
        logging.error(f"خطا در دریافت پیام‌ها از {bot_base_url}: {e}")
        return []

# --- 2️⃣ استخراج اطلاعات پیام ---
def extract_message_data(update: dict):
    message = update.get('message', {})
    from_user = message.get('from', {})
    chat = message.get('chat', {})
    forward = message.get('forward_from', {})
    forward_chat = message.get('forward_from_chat', {})
    forward_origin = message.get('forward_origin', {})

    # استخراج متن پیام
    text = message.get('text', '') or message.get('caption', '') or 'None'

    # استخراج هشتگ‌ها
    import re
    hashtags = ' '.join(tag for tag in re.findall(r'#\w+', text))

    return {
        'update_id': update.get('update_id'),
        'message_id': str(message.get('message_id')),
        'chat_id': chat.get('id'),
        'chat_type': chat.get('type'),
        'chat_title': chat.get('title'),
        'chat_username': chat.get('username'),
        'sender_id': from_user.get('id'),
        'sender_is_bot': from_user.get('is_bot', False),
        'sender_name': f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".strip(),
        'sender_family': f"{from_user.get('last_name', '')}".strip(),
        'sender_username': from_user.get('username'),
        'post_text': message.get('text', '') or message.get('caption', '') or 'None',
        'has_media': any(k in message for k in ['photo', 'video', 'document']),
        'entities': message.get('entities', []),
        'photo_file_id': message.get('photo', [{}])[-1].get('file_id') if message.get('photo') else None,
        'photo_file_unique_id': message.get('photo', [{}])[-1].get('file_unique_id') if message.get('photo') else None,
        'photo_width': message.get('photo', [{}])[-1].get('width') if message.get('photo') else None,
        'photo_height': message.get('photo', [{}])[-1].get('height') if message.get('photo') else None,
        'photo_file_size': message.get('photo', [{}])[-1].get('file_size') if message.get('photo') else None,
        'video_file_id': message.get('video', {}).get('file_id'),
        'video_file_unique_id': message.get('video', {}).get('file_unique_id'),
        'video_width': message.get('video', {}).get('width'),
        'video_height': message.get('video', {}).get('height'),
        'video_duration': message.get('video', {}).get('duration'),
        'video_file_size': message.get('video', {}).get('file_size'),
        'document_file_id': message.get('document', {}).get('file_id'),
        'document_file_unique_id': message.get('document', {}).get('file_unique_id'),
        'document_file_name': message.get('document', {}).get('file_name'),
        'document_mime_type': message.get('document', {}).get('mime_type'),
        'document_file_size': message.get('document', {}).get('file_size'),
        'forward_from_id': forward.get('id'),
        'forward_from_name': f"{forward.get('first_name', '')} {forward.get('last_name', '')}".strip(),
        'forward_from_username': forward.get('username'),
        'forward_date': datetime.fromtimestamp(forward.get('date')).strftime('%Y-%m-%d %H:%M:%S') if forward.get('date') else None,
        'forward_from_chat_id': forward_chat.get('id'),
        'forward_from_chat_title': forward_chat.get('title'),
        'forward_from_chat_username': forward_chat.get('username'),
        'forward_from_message_id': message.get('forward_from_message_id'),
        'forward_origin_type': forward_origin.get('type'),
        'forward_origin_sender_id': forward_origin.get('sender_user', {}).get('id'),
        'forward_origin_sender_name': f"{forward_origin.get('sender_user', {}).get('first_name', '')} {forward_origin.get('sender_user', {}).get('last_name', '')}".strip(),
        'reply_to_message_id': message.get('reply_to_message', {}).get('message_id'),
        'collected_at': datetime.now().strftime('%Y-%m-%d'),  # فقط تاریخ
        # 'caption': text,
        'hashtags': hashtags,
    }

# --- 3️⃣ گرفتن یا ساخت نویسنده ---
def get_or_create_author(sender_name, sender_family, sender_username):
    try:
        if sender_username:
            response = requests.get(f"{AUTHOR_API_URL}?username={sender_username}", headers=HEADERS)
        else:
            response = requests.get(f"{AUTHOR_API_URL}?name={sender_name}&family={sender_family}", headers=HEADERS)

        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]['id']

        # اگر نبود، بساز
        data = {
            "name": sender_name or "نامشخص",
            "family": sender_family or "نامشخص",
            "username": sender_username
        }
        post_response = requests.post(AUTHOR_API_URL, json=data, headers=HEADERS)
        if post_response.status_code in [200, 201]:
            logging.info(f"نویسنده {sender_username or sender_name} با موفقیت اضافه شد.")
            return post_response.json()['id']
        else:
            logging.error(f"خطا در افزودن نویسنده {sender_username or sender_name}: {post_response.text}")
            return None
    except Exception as e:
        logging.error(f"خطا در احراز هویت نویسنده: {e}")
        return None

# --- 4️⃣ گرفتن کانال ---
def get_channel(chat_username):
    if not chat_username:
        return None
    try:
        response = requests.get(CHANNEL_API_URL, headers=HEADERS)
        if response.status_code != 200:
            return None
        channels = response.json()
        for channel in channels:
            if channel.get('channel_id') == '@' + chat_username:
                return channel['id']
        return None
    except Exception as e:
        logging.error(f"خطا در اتصال به API کانال: {e}")
        return None

# --- 5️⃣ ارسال داده به Post API ---
def send_post_to_api(data):
    try:
        response = requests.post(POST_API_URL, json=data, headers=HEADERS)
        if response.status_code in [200, 201]:
            logging.info(f"پست {data['message_id']} با موفقیت اضافه شد.")
        else:
            logging.error(f"خطا در افزودن پست {data['message_id']}: {response.text}")
    except Exception as e:
        logging.error(f"خطا در اتصال به API: {e}")

# --- پردازش یک ربات ---
def process_bot(token):
    bot_base_url = f"https://tapi.bale.ai/bot{token}"
    logging.info(f"در حال پردازش ربات با توکن: {token}")

    last_update_id = 0
    while True:
        try:
            updates = get_all_updates(bot_base_url, offset=last_update_id + 1)
        except Exception as e:
            logging.error(f"خطا در دریافت آپدیت از ربات {token}: {e}")
            break

        if not updates:
            logging.info(f"هیچ آپدیت جدیدی برای ربات {token} وجود ندارد.")
            break

        last_update_id = max(u['update_id'] for u in updates)

        for update in updates:
            message_data = extract_message_data(update)
            msg_id = message_data['message_id']

            if msg_id in SEEN_MESSAGES:
                continue

            SEEN_MESSAGES.add(msg_id)

            # --- استخراج فرستنده ---
            sender_name = message_data.get('sender_name', '').strip()
            sender_family = message_data.get('sender_family', '').strip()
            sender_username = message_data.get('sender_username')

            if not sender_name:
                sender_name = "نامشخص"
            if not sender_family:
                sender_family = "نامشخص"

            # --- نویسنده ---
            author_id = get_or_create_author(sender_name, sender_family, sender_username)
            if not author_id:
                logging.warning(f"نویسنده برای پست {msg_id} یافت نشد.")
                continue

            # --- کانال ---
            channel_id = get_channel(message_data.get('chat_username'))
            if not channel_id:
                logging.warning(f"کانال برای پست {msg_id} یافت نشد. ارسال نشد.")
                continue

            # --- تخصیص و ارسال ---
            message_data['author'] = author_id
            message_data['channel'] = channel_id
            send_post_to_api(message_data)

# --- تابع اصلی ---
def main():
    logging.info("شروع فرآیند جمع‌آوری داده...")

    # ورود به سیستم و گرفتن توکن
    access_token = get_jwt_tokens(os.getenv("API_USERNAME"), os.getenv("API_PASSWORD"))
    if not access_token:
        logging.error("ورود ناموفق. برنامه متوقف شد.")
        return

    set_auth_header(access_token)

    # پردازش همه ربات‌ها
    for token in BOT_TOKENS:
        process_bot(token)
        time.sleep(1)  # تأخیر کوتاه بین ربات‌ها

    # ذخیره پیام‌های دیده‌شده
    save_seen_messages()
    logging.info("فرآیند جمع‌آوری داده به پایان رسید.")

# --- اجرای دوره‌ای ---
if __name__ == "__main__":
    # اولین اجرا فوری
    main()

    # برنامه‌ریزی هر 6 ساعت
    schedule.every(6).hours.do(main)

    logging.info("ربات در حال اجرا است و هر 6 ساعت یکبار فعال می‌شود...")

    while True:
        schedule.run_pending()
        time.sleep(60)  # هر دقیقه چک می‌کند