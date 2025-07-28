import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# Configuration
COOKIES_FILE = 'cookies.json'
TARGET_FILE = 'target.txt'
MESSAGE_FILE = 'message.txt'
DELAY_SECONDS = 10

def load_cookies(driver, path):
    with open(path, 'r') as file:
        cookies = json.load(file)
    for cookie in cookies:
        if 'sameSite' in cookie:
            del cookie['sameSite']
        driver.add_cookie(cookie)

def main():
    # Load UID and Messages
    with open(TARGET_FILE, 'r') as f:
        uid = f.read().strip()
    with open(MESSAGE_FILE, 'r') as f:
        messages = [line.strip() for line in f if line.strip()]

    # Set up browser
    options = Options()
    options.add_argument("--disable-notifications")
    driver = webdriver.Chrome(options=options)

    # Load Facebook and inject cookies
    driver.get("https://www.facebook.com")
    time.sleep(3)
    load_cookies(driver, COOKIES_FILE)
    driver.refresh()
    time.sleep(5)

    # Go to Messenger chat
    driver.get(f"https://www.facebook.com/messages/t/{uid}")
    time.sleep(5)

    # Send each message with 10 sec delay
    for message in messages:
        try:
            msg_box = driver.find_element(By.XPATH, '//div[@aria-label="Message"]')
            msg_box.click()
            time.sleep(1)
            msg_box.send_keys(message)
            msg_box.send_keys(Keys.ENTER)
            print(f"[✔] Sent: {message}")
            time.sleep(DELAY_SECONDS)
        except Exception as e:
            print(f"[✘] Failed to send message: {e}")
            break

    driver.quit()
    print("✅ Done sending all messages.")

if __name__ == "__main__":
    main()
