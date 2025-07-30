# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import time
# from bs4 import BeautifulSoup
import pandas as pd
# import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import random
from datetime import time as tme
# تنظیمات مرورگر
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
# options.add_argument("--headless")  # اگر نمی‌خوای مرورگر باز بشه

driver = webdriver.Chrome(options=options)  # یا از Service استفاده کن اگر ChromeDriver توی PATH نیست

url = "https://eitaa.com/varzesh3_ir/"  # آدرس سایت رو جایگزین کن
driver.get(url)
time.sleep(3)  # صبر کن تا صفحه بارگذاری بشه


last_height = driver.execute_script("return document.body.scrollHeight;")
collected_data = []
seen_keys = set()  # برای جلوگیری از تکراری
no_new_data_count = 0
max_no_data_retries = 3  # حداکثر ۳ بار بدون داده جدید امتحان کنه
last_detected_date = None  # 👈 برای نگه‌داری آخرین تاریخ دیده‌شده


def persian_to_english(s):
    """
    تبدیل اعداد فارسی و عربی به انگلیسی
    مثال: '۱۳:۱۱' → '13:11'
    """
    # جدول تبدیل: شامل اعداد فارسی و عربی
    translation_table = str.maketrans(
        '۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩',  # فارسی و عربی
        '01234567890123456789'       # انگلیسی
    )
    return s.translate(translation_table)


TARGET_DATE = "۵ مرداد"   # 🔁 این رو تغییر بده
TARGET_TIME = "۱۳:۱۱"

clean_time = persian_to_english(TARGET_TIME)  # "13:11"
hour, minute = map(int, clean_time.split(":"))
TARGET_TIME = tme(hour, minute)


while no_new_data_count < max_no_data_retries:
    try:
        # 1. اسکرول به بالای صفحه
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.HOME)
        print("اسکرول به بالا انجام شد...")

        # --- 🔥 خواندن تاریخ موقت: فوراً بعد از اسکرول و قبل از بارگذاری کامل ---
        try:
            # ⚠️ اسم کلاس زیر رو با کلاس واقعی تاریخ موقت در سایت خودت جایگزین کن
            # مثلاً: 'date-marker', 'message-date', 'tgme_widget_message_header', ...
            date_element = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "etme_widget_message_service_date"))
            )
            last_detected_date = date_element.text.strip()
            print(f"📅 تاریخ موقت شناسایی شد: {last_detected_date}")
        except Exception as e:
            # اگر تاریخی نبود یا دیده نشد، از آخرین تاریخ قبلی استفاده می‌کنیم
            print(f"هشدار: تاریخ موقت پیدا نشد. از آخرین تاریخ استفاده می‌شود: {last_detected_date}")

        # 2. صبر کن تا اسپینر بارگذاری ناپدید بشه (اگر وجود داشت)
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "loading-spinner"))
            )
            print("بارگذاری کامل شد (اسپینر ناپدید شد).")
        except TimeoutException:
            print("هشدار: اسپینر خیلی طول کشید یا وجود نداشت.")

        # 3. صبر کن تا حداقل یک پیام جدید ظاهر بشه
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CLASS_NAME, "etme_widget_message_bubble")) > 0
        )

        # 4. الان می‌تونیم صفحه رو بخونیم
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        messages = soup.find_all("div", class_="etme_widget_message_bubble")

        new_items = 0
        for msg in messages:
            text_elem = msg.find("div", class_="etme_widget_message_text js-message_text")
            time_elem = msg.find("time", class_="time")
            views_span = msg.find("span", class_="etme_widget_message_views")

            if not text_elem or not time_elem:
                continue

            text = text_elem.get_text(strip=True)

            timestamp = time_elem.get_text(strip=True)
            clean_time = persian_to_english(timestamp)  # "13:11"
            hour, minute = map(int, clean_time.split(":"))
            post_time = tme(hour, minute)

            views = int(views_span['data-count']) if views_span and views_span.has_attr('data-count') else 0

            if last_detected_date == TARGET_DATE and post_time < TARGET_TIME:
                print(last_detected_date)
                print(post_time)
                # تاریخ یکی هست، ولی زمان کمتر → متوقف شو
                reached_target = True
                break

            key = (text, post_time)  # کلید منحصربفرد

            if key not in seen_keys:
                seen_keys.add(key)
                collected_data.append({
                    "text": text,
                    "timestamp": post_time,
                    "views": views,
                    "date": last_detected_date or "نامشخص"  # ✅ اضافه شد: تاریخ موقت
                })
                new_items += 1

        # 5. بررسی اینکه آیا داده جدیدی اومده
        if new_items == 0:
            no_new_data_count += 1
            print(f"داده جدیدی نیومد. تلاش بی‌نتیجه {no_new_data_count}/{max_no_data_retries}")
        else:
            no_new_data_count = 0
            print(f"✅ {new_items} داده جدید اضافه شد. مجموع: {len(collected_data)}")

        # 6. تأخیر کوچک بین اسکرول‌ها
        time.sleep(random.uniform(1.5, 2.5))

    except Exception as e:
        print(f"❌ خطای کلی در حین اسکرول: {e}")
        no_new_data_count += 1
        time.sleep(2)

print("✅ جمع‌آوری کامل شد.")


df = pd.DataFrame(collected_data)

