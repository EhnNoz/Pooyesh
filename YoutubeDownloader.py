import subprocess
import pandas as pd
import time
import json
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")


df = pd.read_excel('files/arbaeen.xlsx', index_col=False)
my_list = df['لینک مطلب'].tolist()
MAX_SIZE_BYTES = 100 * 1024 * 1024
output_template = "%(title)s.%(ext)s"

for index, item in enumerate(my_list):

    url = item
    print(index)
    proxy = os.getenv("PROXY")
    download_folder = r"F:\sourcecode\Instaloader\youtube/"

    MAX_SIZE_MB = 100  # حداکثر حجم مجاز به مگابایت
    # download_folder = "/مسیر/پوشه/هدف/"  # مثل: "/home/user/Downloads/youtube/"

    # محاسبه حداکثر حجم به بایت
    MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

    # تنظیم نام خروجی
    output_template = f"{download_folder}%(title)s.%(ext)s"

    # مرحله ۱: دریافت اطلاعات ویدئو بدون دانلود
    cmd_info = [
        "yt-dlp",
        "--proxy", proxy,
        "--dump-json",
        "-f", "best",
        url
    ]

    print("🔍 در حال دریافت اطلاعات ویدئو...")
    result = subprocess.run(cmd_info, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print(f"❌ خطا در دریافت اطلاعات: {result.stderr}")
        continue

    # تجزیه JSON
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("❌ مشکل در خواندن اطلاعات JSON")
        exit()

    filesize = info.get('filesize')
    title = info.get('title', 'بدون عنوان')

    # چک کردن حجم
    if filesize is None:
        print("⚠️ حجم فایل مشخص نیست. دانلود لغو شد.")
        continue

    print(f"💾 حجم فایل: {filesize / (1024 * 1024):.2f} مگابایت")

    # مقایسه حجم
    if filesize > MAX_SIZE_BYTES:
        print(f"❌ حجم فایل ({filesize / (1024 * 1024):.2f} مگابایت) از {MAX_SIZE_MB} مگابایت بیشتر است. دانلود لغو شد.")
    else:
        print(f"✅ '{title}' کمتر از {MAX_SIZE_MB} مگابایت است. دانلود آغاز می‌شود...")

        # مرحله ۲: دانلود با پراکسی و ذخیره در فولدر مشخص
        cmd_download = [
            "yt-dlp",
            "--proxy", proxy,
            "-o", output_template,
            "-f", "best",
            url
        ]

        subprocess.run(cmd_download)
        print("✅ دانلود با موفقیت انجام شد!")




# from pytube import YouTube
#
#
# # لینک ویدئو را وارد کنید
# url = "https://www.youtube.com/watch?v=uuj9RE9VYK8"
# yt = YouTube(url)
#
# # دانلود با بهترین کیفیت
# stream = yt.streams.get_highest_resolution()
# stream.download(output_path="downloads/")
#
# print(f"دانلود کامل شد! {yt.title}")