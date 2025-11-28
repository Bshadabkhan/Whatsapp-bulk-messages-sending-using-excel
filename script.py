from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep
import pandas

# Load the Excel data
excel_data = pandas.read_excel('Recipients data.xlsx', sheet_name='Recipients')
contacts = excel_data['Contact'].tolist()
message = excel_data['Message'][0]  # assuming message is same for all

# Setup Chrome options (optional: headless, etc.)
options = Options()
# options.add_argument('--headless')  # Uncomment if you want headless mode
# options.add_argument('--no-sandbox')  # Sometimes useful in Linux
# options.add_argument('--disable-dev-shm-usage')

# Setup Chrome driver with correct Service object
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Open WhatsApp Web
driver.get('https://web.whatsapp.com')
input("🔐 Press ENTER after logging in to WhatsApp Web and your chats are visible...")

# Loop through each contact and send the message
for idx, contact in enumerate(contacts):
    try:
        phone = str(contact)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={message}"
        driver.get(url)
        sent = False

        try:
            # Wait until the Send button appears
            click_btn = WebDriverWait(driver, 35).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Send']"))
            )
        except Exception as e:
            print(f"❌ Message could not be sent to {phone}. Error: {e}")
            continue

        sleep(2)
        click_btn.click()
        sent = True
        sleep(5)

        if sent:
            print(f"✅ Message sent to: {phone}")
    except Exception as e:
        print(f"⚠️ Failed to send message to {contact}. Error: {e}")

# Close browser
driver.quit()
print("✅ Script executed successfully.")



