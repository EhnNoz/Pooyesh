import requests
import time
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

def get_updates(bot_token, offset=None):
    url = f"https://tapi.bale.ai/bot{bot_token}/getUpdates"
    params = {'timeout': 30, 'offset': offset} if offset else {'timeout': 30}

    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        print(f"خطا در دریافت آپدیت‌ها: {e}")
        return None


def copy_message(bot_token, chat_id, from_chat_id, message_id):
    url = f"https://tapi.bale.ai/bot{bot_token}/copyMessage"
    params = {
        "chat_id": chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id
    }

    try:
        response = requests.post(url, json=params)
        result = response.json()

        if response.status_code == 200 and result.get('ok'):
            print(f"پیام با موفقیت کپی شد. شناسه پیام جدید: {result['result']['message_id']}")
            return True
        else:
            print(f"خطا در کپی کردن پیام: {result.get('description')}")
            return False

    except Exception as e:
        print(f"خطا در ارسال درخواست: {e}")
        return False


def main():
    bot_token = os.getenv("BOT_TOKEN_1")
    target_chat_id = "@gharbevahshikhososi"  # چتی که می‌خواهید پیام‌ها به آن فوروارد شوند
    source_chat_id = "@gurgpjz6xa"  # چتی که می‌خواهید پیام‌های آن را مانیتور کنید

    last_update_id = 0

    while True:
        try:
            updates = get_updates(bot_token, last_update_id + 1)
            print(updates)


            if updates and updates.get('ok') and updates.get('result'):
                for update in updates['result']:
                    last_update_id = update['update_id']

                    # فقط پیام‌هایی که از چت مورد نظر هستند را پردازش کنید
                    if 'message' in update and str(update['message']['chat']['id']) == source_chat_id or \
                            update['message']['chat']['username'] == source_chat_id.replace('@', ''):
                        message_id = update['message']['message_id']
                        copy_message(bot_token, target_chat_id, source_chat_id, message_id)

            time.sleep(1)

        except Exception as e:
            print(f"خطا در حلقه اصلی: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()