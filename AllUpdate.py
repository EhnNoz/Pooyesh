import requests
import os
from datetime import datetime
import pandas as pd
import re
# --- تنظیمات ---
BOT_TOKEN = "1366796528:"
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

# --- API URLs ---
AUTHOR_API_URL = "/sapi/rep/authors-update/"
CHANNEL_API_URL = "/sapi/rep/channel-code/"
POST_API_URL = "/sapi/rep/posts/"
LOGIN_URL = "/sapi/token/"
# --- توکن احراز هویت ---

# --- توکن ---
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
            print("ورود موفقیت‌آمیز.")
            return tokens['access']
        else:
            print("خطا در ورود:", response.text)
            return None
    except Exception as e:
        print("خطا در اتصال به API ورود:", e)
        return None

# API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUyMzE5MzA2LCJpYXQiOjE3NTIzMTkwMDYsImp0aSI6IjJkNDA5NTFjZGUwMzQwNTg4YzY2N2Q5NzgwZjVkNGY3IiwidXNlcl9pZCI6MX0.pBKCpJBZDvqR_x2lBLR8i-9MXmDh5bfhQbNHnoQ0ebo"
# if not API_TOKEN:
#     raise ValueError("API_TOKEN is not set in environment variables.")
#
# HEADERS = {
#     "Authorization": f"Bearer {API_TOKEN}",
#     "Content-Type": "application/json"
# }

# --- متغیرهای کمکی ---
SEEN_MESSAGES = set()  # جلوگیری از تکرار پست


# --- 1️⃣ دریافت آپدیت‌ها از تلگرام ---
def get_all_updates(offset: int = 0):
    params = {'offset': offset, 'timeout': 5}
    try:
        response = requests.get(f"{BASE_URL}/getUpdates", params=params)
        response.raise_for_status()
        return response.json().get('result', [])
    except requests.exceptions.RequestException as e:
        print(f"خطا در دریافت پیام‌ها: {e}")
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

    # استخراج هشتگ‌ها (اختیاری)
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
        'sender_family': f"{from_user.get('last_name', '')}",
        'sender_username': from_user.get('username'),

        'post_text': message.get('text'),
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
        'caption': text,
        'hashtags': hashtags,  # مثلاً "iran news politics"
    }


# --- 3️⃣ گرفتن یا ساخت نویسنده ---
def get_or_create_author(sender_name, sender_family, sender_username):
    try:
        if sender_username:
            response = requests.get(f"{AUTHOR_API_URL}?username={sender_username}", headers=HEADERS)
        else:
            response = requests.get(f"{AUTHOR_API_URL}?name={sender_name}&family={sender_family}", headers=HEADERS)

        if response.status_code == 200 and len(response.json()) > 0:
            print(response)
            return response.json()[0]['id']
        print()

        # اگر نبود، بساز
        data = {
            "name": sender_name or "نامشخص",
            "family": sender_family or "نامشخص",
            "username": sender_username
        }

        post_response = requests.post(AUTHOR_API_URL, json=data, headers=HEADERS)
        print(post_response)
        if post_response.status_code in [200, 201]:
            print(f"نویسنده {sender_username or sender_name} با موفقیت اضافه شد.")
            return post_response.json()['id']
        else:
            print(f"خطا در افزودن نویسنده {sender_username or sender_name}: {post_response.text}")
            return None

    except Exception as e:
        print(f"خطا در احراز هویت نویسنده: {e}")
        return None


# --- 4️⃣ گرفتن کانال (اگر وجود نداشت، POST نکن) ---
# def get_channel(chat_username):
#     try:
#         if not chat_username:
#             return None
#
#         response = requests.get(f"{CHANNEL_API_URL}?username={chat_username}", headers=HEADERS)
#         if response.status_code == 200 and len(response.json()) > 0:
#             return response.json()[0]['id']
#         return None
#
#     except Exception as e:
#         print(f"خطا در دریافت کانال: {e}")
#         return None
def get_channel(chat_username):
    if not chat_username:
        return None

    try:
        # گرفتن تمام کانال‌ها
        response = requests.get(CHANNEL_API_URL, headers=HEADERS)
        if response.status_code != 200:
            return None

        channels = response.json()
        for channel in channels:
            if channel.get('channel_id') == '@'+chat_username:
                return channel['id']
        return None

    except Exception as e:
        print(f"خطا در اتصال به API کانال: {e}")
        return None

# --- 5️⃣ ارسال داده به Post API ---
def send_post_to_api(data):
    try:
        response = requests.post(POST_API_URL, json=data, headers=HEADERS)
        if response.status_code in [200, 201]:
            print(f"پست {data['message_id']} با موفقیت اضافه شد.")
        else:
            print(f"خطا در افزودن پست {data['message_id']}: {response.text}")
    except Exception as e:
        print(f"خطا در اتصال به API: {e}")


# --- 6️⃣ تابع اصلی ---
def main():

    access_token = get_jwt_tokens("su-admin", "SuAdmin@1404")
    if not access_token:
        print("ورود ناموفق. برنامه متوقف شد.")
        return

    set_auth_header(access_token)
    last_update_id = 0
    while True:
        updates = get_all_updates(offset=last_update_id + 1)
        if not updates:
            print("هیچ آپدیتی وجود ندارد.")
            break

        last_update_id = max(u['update_id'] for u in updates)
        print(last_update_id)

        for update in updates:
            message_data = extract_message_data(update)

            if message_data['message_id'] in SEEN_MESSAGES:
                continue
            SEEN_MESSAGES.add(message_data['message_id'])

            # --- استخراج اطلاعات فرستنده با مقدار پیش‌فرض ---
            sender_name = message_data.get('sender_name', '').strip()
            sender_family = message_data.get('sender_family', '').strip()
            sender_username = message_data.get('sender_username')

            # --- اگر نام خانوادگی خالی بود، "نامشخص" قرار بده ---
            if not sender_name:
                sender_name = "نامشخص"
            if not sender_family:
                sender_family = "نامشخص"

            # --- نویسنده ---
            author_id = get_or_create_author(sender_name, sender_family, sender_username)
            print(author_id)
            if not author_id:
                print(f"نویسنده برای پست {message_data['message_id']} یافت نشد.")
                continue

            # --- کانال ---
            channel_id = get_channel(message_data.get('chat_username'))
            print(channel_id)
            if not channel_id:
                print(f"کانال برای پست {message_data['message_id']} یافت نشد. داده ارسال نشد.")
                continue

            # --- تخصیص نویسنده و کانال ---
            message_data['author'] = author_id
            message_data['channel'] = channel_id

            # --- ارسال به Post ---
            send_post_to_api(message_data)


if __name__ == "__main__":
    main()