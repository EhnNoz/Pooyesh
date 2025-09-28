import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
import re
import pandas as pd

class EitaaCrawler:
    def __init__(self):
        self.BASE_API_URL = "http://10.32.141.78:8081/api/sapi"
        self.LOGIN_URL = f"{self.BASE_API_URL}/token/"
        self.CHANNEL_API_URL = f"{self.BASE_API_URL}/rep/channel-code/?platform=1"
        self.MEMBERS_API_URL = f"{self.BASE_API_URL}/rep/channel-members/"
        self.access_token = None
        self.session = requests.Session()

    def login(self):
        """عملیات لاگین و دریافت توکن دسترسی"""
        # اطلاعات کاربری - باید با مقادیر واقعی جایگزین شود
        login_data = {
            "username": "su-admin",
            "password": "SuAdmin@1404"
        }

        try:
            response = self.session.post(self.LOGIN_URL, data=login_data)
            response.raise_for_status()

            data = response.json()
            if "access" in data:
                self.access_token = data["access"]
                print("لاگین موفقیت‌آمیز بود")
                return True
            else:
                print("خطا در دریافت توکن دسترسی")
                return False

        except requests.exceptions.RequestException as e:
            print(f"خطا در ارتباط با سرور: {e}")
            return False

    def get_channels(self):
        """دریافت لیست کانال‌های قابل کرال"""
        if not self.access_token:
            if not self.login():
                return None

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = self.session.get(self.CHANNEL_API_URL, headers=headers)

            # اگر توکن منقضی شده باشد، دوباره لاگین می‌کنیم
            if response.status_code == 401:
                print("توکن منقضی شده، در حال لاگین مجدد...")
                if self.login():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    response = self.session.get(self.CHANNEL_API_URL, headers=headers)
                else:
                    return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"خطا در دریافت کانال‌ها: {e}")
            return None

    def crawl_member_count(self, channel_url):
        """کرال تعداد اعضای یک کانال از Eitaa"""
        try:
            response = self.session.get(channel_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            counter_element = soup.find('span', class_='counter_value')

            if counter_element and 'data-count' in counter_element.attrs:
                return counter_element['data-count']
            else:
                print(f"عنصر شمارنده اعضا برای {channel_url} یافت نشد")
                return None

        except requests.exceptions.RequestException as e:
            print(f"خطا در کرال کانال {channel_url}: {e}")
            return None

    def post_member_count(self, channel_id, member_count):
        """ارسال تعداد اعضا به سرور"""
        if not self.access_token:
            if not self.login():
                return False

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        data = {
            "channel": channel_id,
            "member_count": member_count,
            "collected_at": datetime.now().strftime("%Y-%m-%d")
        }

        try:
            response = self.session.post(self.MEMBERS_API_URL, json=data, headers=headers)

            # اگر توکن منقضی شده باشد، دوباره لاگین می‌کنیم
            if response.status_code == 401:
                print("توکن منقضی شده، در حال لاگین مجدد...")
                if self.login():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    response = self.session.post(self.MEMBERS_API_URL, json=data, headers=headers)
                else:
                    return False

            response.raise_for_status()
            print(f"اطلاعات کانال {channel_id} با موفقیت ارسال شد")
            return True

        except requests.exceptions.RequestException as e:
            print(f"خطا در ارسال اطلاعات: {e}")
            return False

    def run(self):
        """اجرای اصلی برنامه"""
        # لاگین اولیه
        if not self.login():
            print("خروج به دلیل خطا در لاگین")
            return

        # دریافت کانال‌ها
        channels = self.get_channels()
        if not channels:
            print("هیچ کانالی دریافت نشد")
            return

        print(f"{len(channels)} کانال دریافت شد")

        # پردازش هر کانال
        for channel in channels:
            channel_id = channel.get('id')
            channel_code = channel.get('channel_id')
            if channel_code.startswith('@'):
                channel_code = channel_code[1:]
            print(channel_code)

            if not channel_code:
                continue

            # ساخت آدرس کانال
            channel_url = f"https://eitaa.com/{channel_code}"

            # کرال تعداد اعضا
            member_count = self.crawl_member_count(channel_url)

            # print()

            if member_count:
                print(f"کانال {channel_code}: {member_count} عضو")
                member_count = int(member_count)
                print(member_count)
                print(type(member_count))
                print(channel_id)

                # ارسال اطلاعات به سرور
                self.post_member_count(channel_id, member_count)
            else:
                print(f"خطا در دریافت تعداد اعضای کانال {channel_code}")

            # تاخیر بین درخواست‌ها برای جلوگیری از بلاک شدن
            time.sleep(2)


class BaleCrawler:
    def __init__(self):
        self.BASE_API_URL = "http://10.32.141.78:8081/api/sapi"
        self.LOGIN_URL = f"{self.BASE_API_URL}/token/"
        self.CHANNEL_API_URL = f"{self.BASE_API_URL}/rep/channel-code/?platform=2"
        self.MEMBERS_API_URL = f"{self.BASE_API_URL}/rep/channel-members/"
        self.access_token = None
        self.session = requests.Session()

    def login(self) -> bool:
        """عملیات لاگین و دریافت توکن دسترسی"""
        login_data = {
            "username": "su-admin",  # جایگزین کنید
            "password": "SuAdmin@1404"  # جایگزین کنید
        }

        try:
            response = self.session.post(self.LOGIN_URL, json=login_data)
            response.raise_for_status()

            data = response.json()
            if "access" in data:
                self.access_token = data["access"]
                # تنظیم هدر پیش‌فرض برای session
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                })
                print("✅ لاگین موفقیت‌آمیز بود")
                return True
            else:
                print("❌ خطا در دریافت توکن دسترسی")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در ارتباط با سرور: {e}")
            return False

    def get_channels(self) -> Optional[List[Dict]]:
        """دریافت لیست کانال‌های قابل کرال"""
        if not self.access_token:
            if not self.login():
                return None

        try:
            response = self.session.get(self.CHANNEL_API_URL)

            # اگر توکن منقضی شده باشد، دوباره لاگین می‌کنیم
            if response.status_code == 401:
                print("🔄 توکن منقضی شده، در حال لاگین مجدد...")
                if self.login():
                    response = self.session.get(self.CHANNEL_API_URL)
                else:
                    return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در دریافت کانال‌ها: {e}")
            return None

    def extract_member_count(self, text: str) -> Optional[int]:
        """استخراج تعداد اعضا از متن"""
        try:
            # حذف کاراکترهای غیر عددی و فاصله
            clean_text = re.sub(r'[^\d\.]', '', text.strip())

            if 'هزار' in text:
                # تبدیل هزار به عدد
                count = float(clean_text) * 1000
            elif 'میلیون' in text:
                # تبدیل میلیون به عدد
                count = float(clean_text) * 1000000
            else:
                # عدد معمولی
                count = float(clean_text)

            return int(count)

        except (ValueError, AttributeError):
            print(f"❌ خطا در تبدیل تعداد اعضا: {text}")
            return None

    def crawl_member_count(self, channel_url: str) -> Optional[int]:
        """کرال تعداد اعضای یک کانال از بله"""
        try:
            response = self.session.get(channel_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # جستجو برای پیدا کردن تعداد اعضا با XPATH مورد نظر
            # این یک روش جایگزین برای پیدا کردن المان است
            member_element = None

            # روش 1: جستجو با کلاس یا ویژگی‌های خاص
            member_elements = soup.find_all('span', class_=lambda x: x and 'member' in x.lower() if x else False)

            # روش 2: جستجو با متن شامل "عضو"
            for span in soup.find_all('span'):
                if 'عضو' in span.get_text():
                    member_element = span
                    break

            if member_element:
                member_text = member_element.get_text().strip()
                print(f"📊 متن پیدا شده: {member_text}")
                return self.extract_member_count(member_text)
            else:
                print(f"❌ عنصر تعداد اعضا برای {channel_url} یافت نشد")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در کرال کانال {channel_url}: {e}")
            return None

    def post_member_count(self, channel_id: str, member_count: int) -> bool:
        """ارسال تعداد اعضا به سرور"""
        if not self.access_token:
            if not self.login():
                return False

        data = {
            "channel": channel_id,
            "member_count": int(member_count),
            "collected_at": datetime.now().strftime("%Y-%m-%d")
        }

        try:
            response = self.session.post(self.MEMBERS_API_URL, json=data)

            # اگر توکن منقضی شده باشد، دوباره لاگین می‌کنیم
            if response.status_code == 401:
                print("🔄 توکن منقضی شده، در حال لاگین مجدد...")
                if self.login():
                    response = self.session.post(self.MEMBERS_API_URL, json=data)
                else:
                    return False

            response.raise_for_status()
            print(f"✅ اطلاعات کانال {channel_id} با موفقیت ارسال شد")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در ارسال اطلاعات: {e}")
            return False

    def run(self):
        """اجرای اصلی برنامه"""
        # لاگین اولیه
        if not self.login():
            print("❌ خروج به دلیل خطا در لاگین")
            return

        # دریافت کانال‌ها
        channels = self.get_channels()
        if not channels:
            print("❌ هیچ کانالی دریافت نشد")
            return

        print(f"📋 {len(channels)} کانال دریافت شد")

        # پردازش هر کانال
        for channel in channels:
            channel_id = channel.get('id')
            channel_code = channel.get('channel_id', '')

            if not channel_code:
                print("⚠️ کد کانال وجود ندارد")
                continue

            # ساخت آدرس کانال بله
            if channel_code.startswith('@'):
                channel_code = channel_code[1:]

            channel_url = f"https://ble.ir/{channel_code}"
            print(f"🌐 پردازش کانال: {channel_url}")

            # کرال تعداد اعضا
            member_count = self.crawl_member_count(channel_url)

            if member_count is not None:
                print(f"👥 کانال {channel_code}: {member_count:,} عضو")

                # ارسال اطلاعات به سرور
                success = self.post_member_count(channel_id, member_count)
                if not success:
                    print(f"❌ خطا در ارسال اطلاعات کانال {channel_code}")
            else:
                print(f"❌ خطا در دریافت تعداد اعضای کانال {channel_code}")

            # تاخیر بین درخواست‌ها برای جلوگیری از بلاک شدن
            print("⏳ منتظر 3 ثانیه...")
            time.sleep(3)
            print()

        print("✅ فرآیند کرال کامل شد")


class DumporCrawler:
    def __init__(self):
        self.BASE_API_URL = "http://10.32.141.78:8081/api/sapi"
        self.LOGIN_URL = f"{self.BASE_API_URL}/token/"
        self.CHANNEL_API_URL = f"{self.BASE_API_URL}/rep/channel-code/?platform=5"
        self.MEMBERS_API_URL = f"{self.BASE_API_URL}/rep/channel-members/"
        self.access_token = None
        self.session = requests.Session()

    def login(self) -> bool:
        """عملیات لاگین و دریافت توکن دسترسی"""
        login_data = {
            "username": "su-admin",  # جایگزین کنید
            "password": "SuAdmin@1404"  # جایگزین کنید
        }

        try:
            response = self.session.post(self.LOGIN_URL, json=login_data)
            response.raise_for_status()

            data = response.json()
            if "access" in data:
                self.access_token = data["access"]
                # تنظیم هدر پیش‌فرض برای session
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                })
                print("✅ لاگین موفقیت‌آمیز بود")
                return True
            else:
                print("❌ خطا در دریافت توکن دسترسی")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در ارتباط با سرور: {e}")
            return False

    def get_channels(self) -> Optional[List[Dict]]:
        """دریافت لیست کانال‌های قابل کرال"""
        if not self.access_token:
            if not self.login():
                return None

        try:
            response = self.session.get(self.CHANNEL_API_URL)

            # اگر توکن منقضی شده باشد، دوباره لاگین می‌کنیم
            if response.status_code == 401:
                print("🔄 توکن منقضی شده، در حال لاگین مجدد...")
                if self.login():
                    response = self.session.get(self.CHANNEL_API_URL)
                else:
                    return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در دریافت کانال‌ها: {e}")
            return None

    def extract_member_count(self, text: str) -> Optional[int]:
        """استخراج تعداد اعضا از متن Dumpor"""
        try:
            # حذف کاراکترهای غیر عددی و فاصله
            clean_text = text.strip().lower()

            # تبدیل k به هزار و m به میلیون
            if 'k' in clean_text:
                number = float(clean_text.replace('k', '')) * 1000
            elif 'm' in clean_text:
                number = float(clean_text.replace('m', '')) * 1000000
            else:
                number = float(clean_text)

            return int(number)

        except (ValueError, AttributeError):
            print(f"❌ خطا در تبدیل تعداد اعضا: {text}")
            return None

    def crawl_member_count(self, channel_url: str) -> Optional[int]:
        """کرال تعداد اعضای یک کانال از Dumpor"""
        try:
            # اضافه کردن هدرها برای جلوگیری از بلاک شدن
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }

            response = requests.get(channel_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # جستجو برای divهای حاوی آمار
            stat_containers = soup.find_all('div',
                                            class_='rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition dark:border-slate-800 dark:bg-slate-900')

            for container in stat_containers:
                # بررسی عنوان (dt) برای پیدا کردن بخش Followers
                title_element = container.find('dt',
                                               class_='flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-400')

                if title_element and 'followers' in title_element.get_text().lower():
                    # پیدا کردن مقدار تعداد فالوورها (dd)
                    count_element = container.find('dd',
                                                   class_='mt-1 text-xl font-semibold tracking-tight text-slate-900 dark:text-white')

                    if count_element:
                        member_text = count_element.get_text().strip()
                        print(f"📊 متن پیدا شده: {member_text}")
                        return self.extract_member_count(member_text)

            # روش جایگزین: جستجوی مستقیم در کل صفحه
            followers_elements = soup.find_all('dd',
                                               class_='mt-1 text-xl font-semibold tracking-tight text-slate-900 dark:text-white')

            for i, element in enumerate(followers_elements):
                # بررسی المان قبلی برای پیدا کردن عنوان Followers
                previous_elements = element.find_previous_siblings()
                for prev_element in previous_elements:
                    if prev_element.name == 'dt' and 'followers' in prev_element.get_text().lower():
                        member_text = element.get_text().strip()
                        print(f"📊 متن پیدا شده (جایگزین): {member_text}")
                        return self.extract_member_count(member_text)

            print(f"❌ عنصر تعداد فالوورها برای {channel_url} یافت نشد")
            return None

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در کرال کانال {channel_url}: {e}")
            return None

    def post_member_count(self, channel_id: str, member_count: int) -> bool:
        """ارسال تعداد اعضا به سرور"""
        if not self.access_token:
            if not self.login():
                return False

        data = {
            "channel": channel_id,
            "member_count": int(member_count),
            "collected_at": (datetime.now()-timedelta(days=0)).strftime("%Y-%m-%d")
        }

        try:
            response = self.session.post(self.MEMBERS_API_URL, json=data)

            # اگر توکن منقضی شده باشد، دوباره لاگین می‌کنیم
            if response.status_code == 401:
                print("🔄 توکن منقضی شده، در حال لاگین مجدد...")
                if self.login():
                    response = self.session.post(self.MEMBERS_API_URL, json=data)
                else:
                    return False

            response.raise_for_status()
            print(f"✅ اطلاعات کانال {channel_id} با موفقیت ارسال شد")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در ارسال اطلاعات: {e}")
            return False

    def run(self):
        """اجرای اصلی برنامه"""
        # لاگین اولیه
        if not self.login():
            print("❌ خروج به دلیل خطا در لاگین")
            return

        # دریافت کانال‌ها
        channels = self.get_channels()
        if not channels:
            print("❌ هیچ کانالی دریافت نشد")
            return

        print(f"📋 {len(channels)} کانال دریافت شد")
        # channels = channels[89:95]

        # پردازش هر کانال
        for channel in channels:
            channel_id = channel.get('id')
            channel_code = channel.get('channel_id', '')

            if not channel_code:
                print("⚠️ کد کانال وجود ندارد")
                continue

            # ساخت آدرس کانال Dumpor
            if channel_code.startswith('@'):
                channel_code = channel_code[1:]

            channel_url = f"https://dumpor.io/v/{channel_code}"
            print(f"🌐 پردازش کانال: {channel_url}")

            # کرال تعداد اعضا
            member_count = self.crawl_member_count(channel_url)

            if member_count is not None:
                print(f"👥 کانال {channel_code}: {member_count:,} عضو")

                # ارسال اطلاعات به سرور
                success = self.post_member_count(channel_id, member_count)
                if not success:
                    print(f"❌ خطا در ارسال اطلاعات کانال {channel_code}")
            else:
                print(f"❌ خطا در دریافت تعداد اعضای کانال {channel_code}")

            # تاخیر بین درخواست‌ها برای جلوگیری از بلاک شدن
            print("⏳ منتظر 5 ثانیه...")
            time.sleep(5)
            print()

        print("✅ فرآیند کرال کامل شد")

class RubikaCrawler:
    def __init__(self):
        self.BASE_API_URL = "http://10.32.141.78:8081/api/sapi"
        self.LOGIN_URL = f"{self.BASE_API_URL}/token/"
        self.CHANNEL_API_URL = f"{self.BASE_API_URL}/rep/channel-code/?platform=4"  # فرض کردم platform=3 برای روبیکا
        self.MEMBERS_API_URL = f"{self.BASE_API_URL}/rep/channel-members/"
        self.access_token = None
        self.session = requests.Session()

    def login(self) -> bool:
        """عملیات لاگین و دریافت توکن دسترسی"""
        login_data = {
            "username": "su-admin",  # جایگزین کنید
            "password": "SuAdmin@1404"  # جایگزین کنید
        }

        try:
            response = self.session.post(self.LOGIN_URL, json=login_data)
            response.raise_for_status()

            data = response.json()
            if "access" in data:
                self.access_token = data["access"]
                # تنظیم هدر پیش‌فرض برای session
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                })
                print("✅ لاگین موفقیت‌آمیز بود")
                return True
            else:
                print("❌ خطا در دریافت توکن دسترسی")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در ارتباط با سرور: {e}")
            return False

    def get_channels(self) -> Optional[List[Dict]]:
        """دریافت لیست کانال‌های قابل کرال"""
        if not self.access_token:
            if not self.login():
                return None

        try:
            response = self.session.get(self.CHANNEL_API_URL)

            # اگر توکن منقضی شده باشد، دوباره لاگین می‌کنیم
            if response.status_code == 401:
                print("🔄 توکن منقضی شده، در حال لاگین مجدد...")
                if self.login():
                    response = self.session.get(self.CHANNEL_API_URL)
                else:
                    return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در دریافت کانال‌ها: {e}")
            return None

    def extract_channel_id_from_name(self, name: str) -> Optional[str]:
        """استخراج channel_id از داخل پرانتز در نام کانال"""
        try:
            # پیدا کردن متن داخل پرانتز
            match = re.search(r'\((.*?)\)', name)
            if match:
                return match.group(1).strip()
            return None
        except (AttributeError, TypeError):
            return None

    def extract_member_count(self, text: str) -> Optional[int]:
        """استخراج تعداد اعضا از متن روبیکا"""
        try:
            # حذف متن فارسی و نگه داشتن فقط اعداد
            numbers_only = re.sub(r'[^\d,]', '', text.strip())
            # حذف کاما و تبدیل به عدد
            clean_number = numbers_only.replace(',', '')
            return int(clean_number)

        except (ValueError, AttributeError):
            print(f"❌ خطا در تبدیل تعداد اعضا: {text}")
            return None

    def crawl_member_count(self, channel_url: str) -> Optional[int]:
        """کرال تعداد اعضای یک کانال از روبیکا"""
        try:
            # اضافه کردن هدرها برای جلوگیری از بلاک شدن
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }

            response = requests.get(channel_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # جستجو برای پیدا کردن تعداد اعضا با کلاس user-last-message
            member_elements = soup.find_all('span', class_='user-last-message')

            for element in member_elements:
                text = element.get_text().strip()
                if 'مشترک' in text:
                    print(f"📊 متن پیدا شده: {text}")
                    return self.extract_member_count(text)

            # روش جایگزین: جستجو در کل صفحه برای متن حاوی "مشترک"
            all_text = soup.get_text()
            lines = all_text.split('\n')
            for line in lines:
                if 'مشترک' in line and any(char.isdigit() for char in line):
                    print(f"📊 متن پیدا شده: {line.strip()}")
                    return self.extract_member_count(line)

            print(f"❌ عنصر تعداد اعضا برای {channel_url} یافت نشد")
            return None

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در کرال کانال {channel_url}: {e}")
            return None

    def post_member_count(self, channel_id: str, member_count: int) -> bool:
        """ارسال تعداد اعضا به سرور"""
        if not self.access_token:
            if not self.login():
                return False

        data = {
            "channel": channel_id,
            "member_count": int(member_count),
            "collected_at": (datetime.now()-timedelta(days=0)).strftime("%Y-%m-%d")
        }

        try:
            response = self.session.post(self.MEMBERS_API_URL, json=data)

            # اگر توکن منقضی شده باشد، دوباره لاگین می‌کنیم
            if response.status_code == 401:
                print("🔄 توکن منقضی شده، در حال لاگین مجدد...")
                if self.login():
                    response = self.session.post(self.MEMBERS_API_URL, json=data)
                else:
                    return False

            response.raise_for_status()
            print(f"✅ اطلاعات کانال {channel_id} با موفقیت ارسال شد")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در ارسال اطلاعات: {e}")
            return False

    def run(self):
        """اجرای اصلی برنامه"""
        # لاگین اولیه
        if not self.login():
            print("❌ خروج به دلیل خطا در لاگین")
            return

        # دریافت کانال‌ها
        channels = self.get_channels()
        if not channels:
            print("❌ هیچ کانالی دریافت نشد")
            return

        print(f"📋 {len(channels)} کانال دریافت شد")

        # پردازش هر کانال
        for channel in channels:
            channel_id = channel.get('id')
            channel_name = channel.get('name', '')
            channel_code_from_api = channel.get('channel_id', '')

            if not channel_name:
                print("⚠️ نام کانال وجود ندارد")
                continue

            # استخراج channel_id از داخل پرانتز در نام کانال
            extracted_channel_id = self.extract_channel_id_from_name(channel_name)

            if not extracted_channel_id:
                print(f"⚠️ نتوانستیم channel_id را از نام '{channel_name}' استخراج کنیم")
                continue

            print(f"📝 نام کانال: {channel_name}")
            print(f"🔍 channel_id استخراج شده: {extracted_channel_id}")

            # ساخت آدرس کانال روبیکا
            channel_url = f"https://rubika.ir/{extracted_channel_id}"
            print(f"🌐 پردازش کانال: {channel_url}")

            # کرال تعداد اعضا
            member_count = self.crawl_member_count(channel_url)

            if member_count is not None:
                print(f"👥 کانال {extracted_channel_id}: {member_count:,} عضو")

                # ارسال اطلاعات به سرور
                success = self.post_member_count(channel_id, member_count)
                if not success:
                    print(f"❌ خطا در ارسال اطلاعات کانال {extracted_channel_id}")
            else:
                print(f"❌ خطا در دریافت تعداد اعضای کانال {extracted_channel_id}")

            # تاخیر بین درخواست‌ها برای جلوگیری از بلاک شدن
            print("⏳ منتظر 4 ثانیه...")
            time.sleep(4)
            print("-" * 50)

        print("✅ فرآیند کرال کامل شد")


class TelegramCrawler:
    def __init__(self):
        self.BASE_API_URL = "http://10.32.141.78:8081/api/sapi"
        self.LOGIN_URL = f"{self.BASE_API_URL}/token/"
        self.CHANNEL_API_URL = f"{self.BASE_API_URL}/rep/channel-code/?platform=3"  # platform=3 برای تلگرام
        self.MEMBERS_API_URL = f"{self.BASE_API_URL}/rep/channel-members/"
        self.access_token = None
        self.session = requests.Session()

    def login(self):
        """عملیات لاگین و دریافت توکن دسترسی"""
        # اطلاعات کاربری - باید با مقادیر واقعی جایگزین شود
        login_data = {
            "username": "su-admin",
            "password": "SuAdmin@1404"
        }

        try:
            response = self.session.post(self.LOGIN_URL, data=login_data)
            response.raise_for_status()

            data = response.json()
            if "access" in data:
                self.access_token = data["access"]
                print("لاگین موفقیت‌آمیز بود")
                return True
            else:
                print("خطا در دریافت توکن دسترسی")
                return False

        except requests.exceptions.RequestException as e:
            print(f"خطا در ارتباط با سرور: {e}")
            return False

    def get_channels(self):
        """دریافت لیست کانال‌های قابل کرال"""
        if not self.access_token:
            if not self.login():
                return None

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = self.session.get(self.CHANNEL_API_URL, headers=headers)

            # اگر توکن منقضی شده باشد، دوباره لاگین می‌کنیم
            if response.status_code == 401:
                print("توکن منقضی شده، در حال لاگین مجدد...")
                if self.login():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    response = self.session.get(self.CHANNEL_API_URL, headers=headers)
                else:
                    return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"خطا در دریافت کانال‌ها: {e}")
            return None

    def extract_member_count(self, text):
        """استخراج تعداد اعضا از متن تلگرام"""
        try:
            # حذف کاراکترهای غیر عددی و فاصله
            numbers_only = ''.join(filter(str.isdigit, text))
            return int(numbers_only)
        except (ValueError, AttributeError):
            print(f"خطا در تبدیل تعداد اعضا: {text}")
            return None

    def crawl_member_count(self, channel_url):
        """کرال تعداد اعضای یک کانال از تلگرام"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = self.session.get(channel_url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # جستجو برای div با کلاس tgme_page_extra که شامل تعداد اعضا است
            member_element = soup.find('div', class_='tgme_page_extra')

            if member_element:
                member_text = member_element.get_text().strip()
                print(f"متن پیدا شده: {member_text}")

                # استخراج عدد از متن
                return self.extract_member_count(member_text)
            else:
                print(f"عنصر تعداد اعضا برای {channel_url} یافت نشد")
                return None

        except requests.exceptions.RequestException as e:
            print(f"خطا در کرال کانال {channel_url}: {e}")
            return None

    def post_member_count(self, channel_id, member_count):
        """ارسال تعداد اعضا به سرور"""
        if not self.access_token:
            if not self.login():
                return False

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        data = {
            "channel": channel_id,
            "member_count": member_count,
            "collected_at": datetime.now().strftime("%Y-%m-%d")
        }

        try:
            response = self.session.post(self.MEMBERS_API_URL, json=data, headers=headers)

            # اگر توکن منقضی شده باشد، دوباره لاگین می‌کنیم
            if response.status_code == 401:
                print("توکن منقضی شده، در حال لاگین مجدد...")
                if self.login():
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    response = self.session.post(self.MEMBERS_API_URL, json=data, headers=headers)
                else:
                    return False

            response.raise_for_status()
            print(f"اطلاعات کانال {channel_id} با موفقیت ارسال شد")
            return True

        except requests.exceptions.RequestException as e:
            print(f"خطا در ارسال اطلاعات: {e}")
            return False

    # def run(self):
    #     """اجرای اصلی برنامه"""
    #     # لاگین اولیه
    #     if not self.login():
    #         print("خروج به دلیل خطا در لاگین")
    #         return
    #
    #     # دریافت کانال‌ها
    #     channels = self.get_channels()
    #     if not channels:
    #         print("هیچ کانالی دریافت نشد")
    #         return
    #
    #     print(f"{len(channels)} کانال دریافت شد")
    #
    #     # پردازش هر کانال
    #     for channel in channels:
    #         channel_id = channel.get('id')
    #         channel_code = channel.get('channel_id')
    #
    #         if not channel_code:
    #             continue
    #
    #         # حذف @ از ابتدای نام کانال اگر وجود دارد
    #         if channel_code.startswith('@'):
    #             channel_code = channel_code[1:]
    #
    #         print(channel_code)
    #
    #         # ساخت آدرس کانال تلگرام
    #         channel_url = f"https://t.me/{channel_code}"
    #
    #         # کرال تعداد اعضا
    #         member_count = self.crawl_member_count(channel_url)
    #
    #         if member_count:
    #             print(f"کانال {channel_code}: {member_count} عضو")
    #             member_count = int(member_count)
    #             print(member_count)
    #             print(type(member_count))
    #             print(channel_id)
    #
    #             # ارسال اطلاعات به سرور
    #             self.post_member_count(channel_id, member_count)
    #         else:
    #             print(f"خطا در دریافت تعداد اعضای کانال {channel_code}")
    #
    #         # تاخیر بین درخواست‌ها برای جلوگیری از بلاک شدن
    #         time.sleep(2)

    def run(self):
        """اجرای اصلی برنامه با قابلیت مدیریت پروکسی و ذخیره در DataFrame"""
        # لاگین اولیه
        if not self.login():
            print("خروج به دلیل خطا در لاگین")
            return

        # دریافت کانال‌ها
        channels = self.get_channels()
        if not channels:
            print("هیچ کانالی دریافت نشد")
            return

        print(f"{len(channels)} کانال دریافت شد")

        # لیستی برای ذخیره داده‌های جمع‌آوری شده
        collected_data = []

        # ⏸️ تاخیر 30 ثانیه برای روشن کردن پروکسی
        print("⏳ لطفاً پروکسی را روشن کنید. 30 ثانیه وقت دارید...")
        time.sleep(30)

        # پردازش هر کانال (فقط کرال و ذخیره در DataFrame)
        for channel in channels:
            channel_id = channel.get('id')
            channel_code = channel.get('channel_id')

            if not channel_code:
                continue

            # حذف @ از ابتدای نام کانال اگر وجود دارد
            if channel_code.startswith('@'):
                channel_code = channel_code[1:]

            print(f"در حال کرال کانال: {channel_code}")

            # ساخت آدرس کانال تلگرام
            channel_url = f"https://t.me/{channel_code}"  # ❗ فاصله اضافی حذف شد

            # کرال تعداد اعضا
            member_count = self.crawl_member_count(channel_url)

            if member_count:
                print(f"کانال {channel_code}: {member_count} عضو")
                collected_data.append({
                    'channel_id': channel_id,
                    'channel_code': channel_code,
                    'member_count': int(member_count),
                    'collected_at': datetime.now().strftime("%Y-%m-%d")
                })
            else:
                print(f"خطا در دریافت تعداد اعضای کانال {channel_code}")

            # تاخیر بین درخواست‌ها برای جلوگیری از بلاک شدن
            time.sleep(2)

        # ✅ ذخیره داده‌ها در DataFrame
        df = pd.DataFrame(collected_data)
        print("\n📊 داده‌های جمع‌آوری شده:")
        print(df)

        # ⏸️ تاخیر 30 ثانیه برای خاموش کردن پروکسی
        print("\n⏳ لطفاً پروکسی را خاموش کنید. 30 ثانیه وقت دارید...")
        time.sleep(30)

        # 📤 ارسال داده‌ها به API (بعد از خاموش کردن پروکسی)
        print("\n📤 شروع ارسال داده‌ها به سرور...")
        for record in collected_data:
            success = self.post_member_count(record['channel_id'], record['member_count'])
            if not success:
                print(f"❌ ارسال برای کانال {record['channel_code']} ناموفق بود.")
            time.sleep(1)  # کمی تاخیر بین ارسال‌ها

        print("✅ عملیات کامل شد.")



# اجرای برنامه
if __name__ == "__main__":
    # crawler = EitaaCrawler()
    # crawler = BaleCrawler()
    # crawler = DumporCrawler()
    crawler = RubikaCrawler()
    # crawler = TelegramCrawler()
    crawler.run()

