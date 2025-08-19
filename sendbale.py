import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
# تنظیمات
# TOKEN = 'توکن_ربات_تو'
# CHANNEL_ID = '@username_kanal'  # یا -1001234567890
# FOLDER_PATH = '/مسیر/فولدر/ویدیوها'



# گرفتن لیست ویدیوها
video_files = [f for f in os.listdir(r'E:\arbaen\08') if f.endswith(('.mp4', '.avi', '.mkv'))]
selected_videos = video_files[::-1]
# selected_videos = selected_videos[131:]  # فقط ۱۰۰ تا اولی

# ارسال هر ویدیو
for idx, video_file in enumerate(selected_videos):
    file_path = os.path.join(r'E:\arbaen\08', video_file)
    print(f"در حال آپلود ویدیوی {idx+1}: {video_file}")
    try:
        with open(file_path, 'rb') as video:
            apiURL = os.getenv("API_SEND_BALE")
            response = requests.post(apiURL, data={'chat_id': '@rasadarbaeen1404', 'caption': '#رصد_اربعین'},
                                     files={'video': video})

            # bot.send_video(chat_id=CHANNEL_ID, video=video, caption=video_file)
        print(f"ویدیوی {video_file} با موفقیت ارسال شد.")
    except Exception as e:
        print(f"خطا در ارسال {video_file}: {e}")