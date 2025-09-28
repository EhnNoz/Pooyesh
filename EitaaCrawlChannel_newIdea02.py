from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import re
from datetime import datetime


class EitaaCrawlerImproved:
    def __init__(self):
        # تنظیمات مرورگر
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 25)
        self.messages_data = []

    def manual_login(self):
        """منتظر ماندن برای لاگین دستی"""
        print("🎯 در حال باز کردن صفحه Eitaa...")
        self.driver.get("https://web.eitaa.com/#@hameyema")

        print("📱 لطفاً مراحل زیر را انجام دهید:")
        print("1. شماره تلفن را وارد کنید")
        print("2. دکمه 'ادامه' را بزنید")
        print("3. کد تأیید را وارد کنید")
        print("4. پس از ورود به کانال، اینجا Enter بزنید")

        input("⏳ پس از تکمیل لاگین، Enter را فشار دهید...")
        time.sleep(5)
        return True

    def scroll_to_top(self):
        """اسکرول به بالاترین نقطه برای دیدن جدیدترین پیام‌ها"""
        try:
            scrollable = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".scrollable.scrollable-y"))
            )
            self.driver.execute_script("arguments[0].scrollTop = 0;", scrollable)
            time.sleep(3)
            return scrollable
        except:
            return None

    def detect_content_type(self, message_element):
        """تشخیص نوع محتوای پست با جستجو در والدین"""
        try:
            # پیدا کردن والد bubble-content-wrapper
            parent_wrapper = message_element.find_element(By.XPATH,
                                                          "./ancestor::div[contains(@class, 'bubble-content-wrapper')]")

            # بررسی ویدیو در داخل attachment
            video_elements = parent_wrapper.find_elements(By.CSS_SELECTOR, "video.media-video")
            if video_elements:
                return "video/mp4"

            # بررسی عکس در داخل attachment
            img_elements = parent_wrapper.find_elements(By.CSS_SELECTOR, "img.media-photo")
            if img_elements:
                return "image/jpeg"

            # بررسی صوت در داخل attachment
            audio_elements = parent_wrapper.find_elements(By.CSS_SELECTOR, "div.audio-play-icon")
            if audio_elements:
                return "audio/mp3"

            return ""  # اگر هیچکدام نبود، خالی برگردان

        except Exception as e:
            print(f"خطا در تشخیص نوع محتوا: {e}")
            return ""

    def check_forwarded_post(self, message_element):
        """بررسی اینکه پست فورواردی است یا نه و استخراج منبع"""
        try:
            # پیدا کردن والد bubble-content-wrapper
            parent_wrapper = message_element.find_element(By.XPATH,
                                                          "./ancestor::div[contains(@class, 'bubble-content-wrapper')]")

            # بررسی وجود بخش فوروارد
            forward_elements = parent_wrapper.find_elements(By.CSS_SELECTOR, "div.name")
            if forward_elements:
                # استخراج منبع فوروارد
                peer_title_elements = parent_wrapper.find_elements(By.CSS_SELECTOR, "span.peer-title")
                if peer_title_elements:
                    source = peer_title_elements[0].text
                    return True, source
            return False, ""

        except Exception as e:
            print(f"خطا در بررسی فوروارد: {e}")
            return False, ""

    def extract_hashtags(self, text):
        """استخراج هشتگ‌ها از متن"""
        try:
            # الگو برای پیدا کردن هشتگ‌های فارسی و انگلیسی
            hashtag_pattern = r'#([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FFa-zA-Z0-9_]+)'
            hashtags = re.findall(hashtag_pattern, text)
            return ' '.join(hashtags) if hashtags else ""
        except:
            return ""

    def extract_message_id(self, message_element):
        """استخراج message_id از data-mid"""
        try:
            # پیدا کردن والد bubble که دارای data-mid است
            bubble_element = message_element.find_element(By.XPATH,
                                                         "./ancestor::div[contains(@class, 'bubble')][@data-mid]")
            message_id = bubble_element.get_attribute('data-mid')
            return message_id if message_id else ""
        except Exception as e:
            print(f"خطا در استخراج message_id: {e}")
            return ""

    def extract_post_info(self, message_element):
        """استخراج اطلاعات کامل از هر پست"""
        try:
            # دریافت HTML داخلی
            html_content = message_element.get_attribute('innerHTML')

            # استخراج متن تمیز
            clean_text = re.sub(r'<a[^>]*>@[^<]*</a>', '', html_content)  # حذف mention
            clean_text = re.sub(r'<span[^>]*time[^>]*>.*?</span>', '', clean_text)
            clean_text = re.sub(r'<div[^>]*inner[^>]*>.*?</div>', '', clean_text)
            clean_text = re.sub(r'<i[^>]*>.*?</i>', '', clean_text)
            clean_text = re.sub(r'<[^>]*>', ' ', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

            # استخراج زمان
            time_match = re.search(r'title="([^"]*)"', html_content)
            post_time = time_match.group(1) if time_match else "زمان نامشخص"

            # استخراج بازدیدها - با تاخیر برای لود شدن ویوها
            time.sleep(1)  # تاخیر برای لود شدن ویوها
            views_match = re.search(r'<span class="post-views">(\d+)</span>', html_content)
            views = views_match.group(1) if views_match else "0"

            # تشخیص نوع محتوا
            content_type = self.detect_content_type(message_element)

            # استخراج هشتگ‌ها
            hashtags = self.extract_hashtags(clean_text)

            # بررسی فورواردی بودن پست
            is_forwarded, forward_source = self.check_forwarded_post(message_element)

            # اگر پست فورواردی بود، بازدید را صفر قرار بده
            if is_forwarded:
                views = "0"

            # استخراج message_id
            message_id = self.extract_message_id(message_element)

            # تاریخچه استخراج
            extraction_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return {
                'message_id': message_id,
                'post_text': clean_text,
                'date': post_time,
                'views': views,
                'document_mime_type': content_type,
                'hashtags': hashtags,
                'is_forwarded': "بله" if is_forwarded else "خیر",
                'forward_from_chat_title': forward_source if is_forwarded else "",
                'collected_at': extraction_time,
                'full_text': message_element.text
            }

        except Exception as e:
            print(f"❌ خطا در استخراج پست: {e}")
            return None

    def collect_posts(self, max_posts=50):
        """جمع‌آوری پست‌ها"""
        print("🔍 در حال جستجوی پست‌ها...")

        try:
            # اسکرول به بالا
            scrollable = self.scroll_to_top()
            if not scrollable:
                print("❌ کانتینر اسکرول پیدا نشد")
                return False

            post_count = 0
            unique_posts = set()
            scroll_attempts = 0

            while post_count < max_posts and scroll_attempts < 15:
                # پیدا کردن تمام پست‌ها
                posts = self.driver.find_elements(By.CSS_SELECTOR, "div.message[dir='auto']")
                print(f"📄 تعداد پست‌های پیدا شده: {len(posts)}")

                for post in posts:
                    if post_count >= max_posts:
                        break

                    post_info = self.extract_post_info(post)
                    if post_info and post_info['post_text'] not in unique_posts:
                        unique_posts.add(post_info['post_text'])
                        self.messages_data.append(post_info)
                        post_count += 1

                        # نمایش اطلاعات پست
                        content_type_icon = ""
                        if post_info['document_mime_type'] == "video/mp4":
                            content_type_icon = "🎥"
                        elif post_info['document_mime_type'] == "image/jpeg":
                            content_type_icon = "🖼️"
                        elif post_info['document_mime_type'] == "audio/mp3":
                            content_type_icon = "🔊"

                        hashtag_info = f" - هشتگ: {post_info['hashtags']}" if post_info['hashtags'] else ""

                        # اطلاعات فوروارد
                        forward_info = f" - 🔄 فوروارد از: {post_info['forward_from_chat_title']}" if post_info['is_forwarded'] == "بله" else ""

                        # اطلاعات message_id
                        mid_info = f" - ID: {post_info['message_id']}" if post_info['message_id'] else ""

                        print(f"✅ پست {post_count} {content_type_icon} اضافه شد{mid_info}{hashtag_info}{forward_info}")

                if post_count >= max_posts:
                    break

                # اسکرول کمی پایین‌تر برای بارگذاری پست‌های بیشتر
                self.driver.execute_script(
                    "arguments[0].scrollTop += 500;",
                    scrollable
                )
                scroll_attempts += 1
                time.sleep(2)

            print(f"🎉 جمع‌آوری کامل! تعداد پست‌ها: {post_count}")
            return True

        except Exception as e:
            print(f"❌ خطا در جمع‌آوری پست‌ها: {e}")
            return False

    def save_to_excel(self):
        """ذخیره در فایل اکسل"""
        if not self.messages_data:
            print("⚠️ هیچ داده‌ای برای ذخیره‌سازی وجود ندارد")
            return False

        try:
            filename = f"eitaa_posts_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            df = pd.DataFrame(self.messages_data)

            # مرتب‌سازی بر اساس زمان ارسال (جدیدترین اول)
            if 'date' in df.columns:
                try:
                    df = df.sort_values('date', ascending=False)
                except:
                    pass

            df.to_excel(filename, index=False, engine='openpyxl')

            print(f"💾 فایل اکسل با نام '{filename}' ذخیره شد")
            print(f"📊 تعداد رکوردها: {len(self.messages_data)}")

            # نمایش آمار انواع محتوا
            content_stats = df['document_mime_type'].value_counts()
            print("\n📈 آمار انواع محتوا:")
            for content_type, count in content_stats.items():
                type_name = "متن ساده" if content_type == "" else content_type
                print(f"   - {type_name}: {count} پست")

            # نمایش آمار هشتگ‌ها
            hashtag_posts = df[df['hashtags'] != ''].shape[0]
            print(f"   - پست‌های دارای هشتگ: {hashtag_posts}")

            # نمایش آمار فورواردها
            forwarded_posts = df[df['is_forwarded'] == 'بله'].shape[0]
            print(f"   - پست‌های فورواردی: {forwarded_posts}")

            # نمایش آمار message_id
            posts_with_id = df[df['message_id'] != ''].shape[0]
            print(f"   - پست‌های دارای message_id: {posts_with_id}")

            return True

        except Exception as e:
            print(f"❌ خطا در ذخیره‌سازی اکسل: {e}")
            return False

    def run(self):
        """اجرای اصلی"""
        try:
            if self.manual_login():
                if self.collect_posts(50):
                    self.save_to_excel()
        except Exception as e:
            print(f"❌ خطای کلی: {e}")
        finally:
            input("\n👋 برای بستن مرورگر Enter بزنید...")
            self.driver.quit()


# اجرای برنامه
if __name__ == "__main__":
    print("🚀 شروع کرالر Eitaa...")
    crawler = EitaaCrawlerImproved()
    crawler.run()