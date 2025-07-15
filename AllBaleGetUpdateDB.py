import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict, Any
import psycopg2
from sqlalchemy import create_engine
from psycopg2 import sql
from sqlalchemy import create_engine, text

BOT_TOKEN = "286348672:N9rQ7rGrYj5htzkRax9H7t4HJQpNa1UBcIxgetna"
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

# تنظیمات اتصال به PostgreSQL با SQLAlchemy
DATABASE_URI = "postgresql://postgres:R12345eza@10.32.141.8/Ehsan"

# ایجاد موتور اتصال
engine = create_engine(DATABASE_URI, pool_size=20, max_overflow=100)


def get_all_updates(offset: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """دریافت تمام آپدیت‌ها با مدیریت offset چندگانه"""
    all_results = []

    while True:
        params = {'offset': offset, 'timeout': 10}
        try:
            response = requests.get(f"{BASE_URL}/getUpdates", params=params)
            response.raise_for_status()
            results = response.json().get('result', [])

            if not results:
                print("هیچ آپدیتی موجود نیست.")
                break

            all_results.extend(results)
            offset = results[-1]['update_id'] + 1  # به‌روزرسانی offset برای درخواست بعدی

            print(f"دریافت {len(results)} آپدیت دیگر. جمع کل: {len(all_results)}")

        except requests.exceptions.RequestException as e:
            print(f"خطا در دریافت پیام‌ها: {e}")
            break

    return all_results


def get_new_updates() -> List[Dict[str, Any]]:
    """دریافت آپدیت‌های جدید با مدیریت offset"""
    last_update_id = get_last_update_id_from_db()
    print(f"آخرین update_id در دیتابیس: {last_update_id}")

    # دریافت آپدیت‌ها از نقطه‌ی بعد از آخرین update_id
    updates = get_all_updates(offset=last_update_id + 1)

    if updates:
        new_offset = updates[-1].get('update_id') + 1
        print(f"{len(updates)} آپدیت جدید دریافت شد. جدیدترین offset: {new_offset}")
        return updates
    else:
        print("آپدیت جدیدی وجود ندارد.")
        return []


def extract_media_info(message: Dict[str, Any]) -> Dict[str, Any]:
    """استخراج اطلاعات رسانه‌های مختلف"""
    media_types = ['photo', 'video', 'document', 'audio', 'voice', 'video_note', 'animation', 'sticker']
    media_info = {}

    for media_type in media_types:
        if media_type in message:
            media_data = message[media_type]
            if isinstance(media_data, list):  # برای عکس‌ها که لیست هستند
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
            if message.get('forward_date') else None
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

    message_data = {
        'update_id': update['update_id'],
        'message_id': message.get('message_id'),
        'date': datetime.fromtimestamp(message['date']).strftime('%Y-%m-%d %H:%M:%S') if message.get('date') else None,
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

    message_data.update(extract_media_info(message))
    message_data.update(extract_forward_info(message))

    return message_data


def create_messages_dataframe(updates: List[Dict[str, Any]]) -> pd.DataFrame:
    """تبدیل لیست آپدیت‌ها به دیتافریم"""
    if not updates:
        return pd.DataFrame()

    messages_data = [extract_message_data(update) for update in updates]
    df = pd.DataFrame(messages_data)

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

    existing_columns = [col for col in columns_order if col in df.columns]
    return df[existing_columns]


def save_to_excel(df: pd.DataFrame, filename: str = "telegram_messages.xlsx"):
    """ذخیره دیتافریم در فایل اکسل"""
    if not df.empty:
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"دیتافریم با موفقیت در فایل '{filename}' ذخیره شد.")
    else:
        print("دیتایی برای ذخیره وجود ندارد.")


def get_last_update_id_from_db() -> int:
    """دریافت آخرین update_id از دیتابیس"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(update_id) FROM telegram_messages")).fetchone()[0]
            return int(result) if result is not None else 0
    except Exception as e:
        print(f"خطا در خواندن از دیتابیس: {e}")
        return 0


def save_to_database(df: pd.DataFrame):
    """ذخیره دیتافریم در دیتابیس با استفاده از to_sql"""
    if not df.empty:
        with engine.connect() as conn:
            df.to_sql('telegram_messages', con=conn, if_exists='append', index=False)
            print(f"{len(df)} رکورد با موفقیت به دیتابیس اضافه شد.")
    else:
        print("دیتایی برای ذخیره در دیتابیس وجود ندارد.")


def main():
    print("در حال دریافت آپدیت‌های جدید از Bale...")

    all_updates = get_new_updates()

    if all_updates:
        messages_df = create_messages_dataframe(all_updates)

        if not messages_df.empty:
            print("\n✅ نمونه‌ای از داده‌های استخراج شده:")
            print(messages_df.head())

            save_to_excel(messages_df)
            save_to_database(messages_df)
        else:
            print("⚠️ هیچ پیام معتبری استخراج نشد.")
    else:
        print("❌ هیچ آپدیت جدیدی دریافت نشد.")


if __name__ == "__main__":
    main()

# def run_polling():
#     print("Polling شروع شد...")
#     while True:
#         last_offset = get_last_offset_from_db()
#         updates = get_updates(offset=last_offset + 1)
#
#         if updates:
#             process_updates(updates)
#             new_offset = updates[-1]['update_id'] + 1
#             save_offset_to_db(new_offset)
#             print(f"آخرین update_id: {new_offset}")
#
#         # منتظر بمانید قبل از درخواست بعدی (برای جلوگیری از overload)
#         time.sleep(1)
#
# if __name__ == "__main__":
#     run_polling()