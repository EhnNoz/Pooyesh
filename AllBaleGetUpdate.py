import pandas as pd
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")

BOT_TOKEN = os.getenv("BOT_TOKEN_2")
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

# TARGET_CHAT_ID = "iranemankhososi"  # می‌تواند عددی (برای چت خصوصی) یا @ChannelName باشد


def get_all_updates(offset: int = 0) -> List[Dict[str, Any]]:
    """دریافت تمام آپدیت‌ها از تلگرام"""
    params = {'offset': offset, 'timeout': 5}
    try:
        response = requests.get(f"{BASE_URL}/getUpdates", params=params)
        response.raise_for_status()
        return response.json().get('result', [])
    except requests.exceptions.RequestException as e:
        print(f"خطا در دریافت پیام‌ها: {e}")
        return []


def extract_media_info(message: Dict[str, Any]) -> Dict[str, Any]:
    """استخراج اطلاعات رسانه‌های مختلف"""
    media_types = ['photo', 'video', 'document', 'audio', 'voice', 'video_note', 'animation', 'sticker']
    media_info = {}

    for media_type in media_types:
        if media_type in message:
            media_data = message[media_type]
            if isinstance(media_data, list):  # برای عکس‌ها که آرایه هستند
                media_data = media_data[-1]  # بزرگترین سایز

            prefix = f"{media_type}_"
            for key, value in media_data.items():
                media_info[f"{prefix}{key}"] = value

    return media_info


def extract_forward_info(message: Dict[str, Any]) -> Dict[str, Any]:
    """استخراج اطلاعات پیام‌های فوروارد شده"""
    forward_info = {}

    if 'forward_from' in message:
        forward_info.update({
            'forward_from_id': message['forward_from'].get('id'),
            'forward_from_name': message['forward_from'].get('first_name', '') + ' ' +
                                 message['forward_from'].get('last_name', ''),
            'forward_from_username': message['forward_from'].get('username'),
            'forward_date': datetime.fromtimestamp(message['forward_date']).strftime('%Y-%m-%d %H:%M:%S')
            if 'forward_date' in message else None
        })

    if 'forward_from_chat' in message:
        forward_info.update({
            'forward_from_chat_id': message['forward_from_chat'].get('id'),
            'forward_from_chat_title': message['forward_from_chat'].get('title'),
            'forward_from_chat_username': message['forward_from_chat'].get('username'),
            'forward_from_message_id': message.get('forward_from_message_id')
        })

    if 'forward_origin' in message:
        forward_info['forward_origin_type'] = message['forward_origin'].get('type')
        if message['forward_origin'].get('type') == 'user':
            sender = message['forward_origin'].get('sender_user', {})
            forward_info.update({
                'forward_origin_sender_id': sender.get('id'),
                'forward_origin_sender_name': sender.get('first_name', '') + ' ' +
                                              sender.get('last_name', '')
            })

    return forward_info


def extract_message_data(update: Dict[str, Any]) -> Dict[str, Any]:
    """استخراج ساختار کامل داده‌های پیام"""
    message = update.get('message', {})
    from_user = message.get('from', {})
    chat = message.get('chat', {})

    # اطلاعات پایه
    message_data = {
        'update_id': update['update_id'],
        'message_id': message.get('message_id'),
        'date': datetime.fromtimestamp(message.get('date')).strftime('%Y-%m-%d %H:%M:%S'),
        'chat_id': chat.get('id'),
        'chat_type': chat.get('type'),
        'chat_title': chat.get('title'),
        'chat_username': chat.get('username'),
        'sender_id': from_user.get('id'),
        'sender_is_bot': from_user.get('is_bot', False),
        'sender_name': from_user.get('first_name', '') + ' ' + from_user.get('last_name', ''),
        'sender_username': from_user.get('username'),
        'text': message.get('text'),
        'caption': message.get('caption'),
        'has_media': any(key in message for key in ['photo', 'video', 'document', 'audio', 'voice']),
        'entities': str(message.get('entities', [])),
        'reply_to_message_id': message.get('reply_to_message', {}).get('message_id')
        if 'reply_to_message' in message else None
    }

    # اضافه کردن اطلاعات رسانه‌ها
    message_data.update(extract_media_info(message))

    # اضافه کردن اطلاعات فوروارد
    message_data.update(extract_forward_info(message))

    return message_data


def create_messages_dataframe(updates: List[Dict[str, Any]]) -> pd.DataFrame:
    """تبدیل لیست آپدیت‌ها به دیتافریم"""
    if not updates:
        return pd.DataFrame()

    messages_data = [extract_message_data(update) for update in updates]
    df = pd.DataFrame(messages_data)

    # مرتب کردن ستون‌ها برای خوانایی بهتر
    columns_order = [
        'update_id', 'message_id', 'date', 'chat_id', 'chat_type', 'chat_title', 'chat_username',
        'sender_id', 'sender_is_bot', 'sender_name', 'sender_username', 'text', 'caption',
        'has_media', 'photo_file_id', 'photo_file_unique_id', 'photo_width', 'photo_height',
        'photo_file_size', 'video_file_id', 'video_file_unique_id', 'video_width', 'video_height',
        'video_duration', 'video_file_size', 'document_file_id', 'document_file_unique_id',
        'document_file_name', 'document_mime_type', 'document_file_size',
        'forward_from_id', 'forward_from_name', 'forward_from_username', 'forward_date',
        'forward_from_chat_id', 'forward_from_chat_title', 'forward_from_chat_username',
        'forward_from_message_id', 'forward_origin_type', 'forward_origin_sender_id',
        'forward_origin_sender_name', 'entities', 'reply_to_message_id'
    ]

    # فقط ستون‌هایی که در داده وجود دارند را نگه دارید
    existing_columns = [col for col in columns_order if col in df.columns]
    return df[existing_columns]


def save_to_excel(df: pd.DataFrame, filename: str = "telegram_messages.xlsx"):
    """ذخیره دیتافریم در فایل اکسل"""
    if not df.empty:
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"دیتافریم با موفقیت در فایل '{filename}' ذخیره شد.")
    else:
        print("دیتایی برای ذخیره وجود ندارد.")


def main():
    print("دریافت پیام‌ها از تلگرام و ساخت دیتافریم...")

    # دریافت همه آپدیت‌ها
    all_updates = get_all_updates(offset=0)

    if all_updates:
        print(f"تعداد کل آپدیت‌های دریافت شده: {len(all_updates)}")

        # ساخت دیتافریم
        messages_df = create_messages_dataframe(all_updates)

        if not messages_df.empty:
            print("\nنمونه‌ای از داده‌های استخراج شده:")
            print(messages_df.head())

            # ذخیره در فایل اکسل
            save_to_excel(messages_df)
        else:
            print("هیچ پیام معتبری برای نمایش یافت نشد.")
    else:
        print("هیچ آپدیتی دریافت نشد.")


if __name__ == "__main__":
    main()