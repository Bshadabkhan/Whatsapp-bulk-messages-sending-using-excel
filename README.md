🚀 WhatsApp Bulk Message Sender (Without Saving Contacts)

Automate WhatsApp Web to send bulk messages without saving phone numbers.
This Python-driven automation reads contacts from an Excel file and sends personalized or pre-defined messages automatically using Selenium.

Ideal for promotions, client communication, bulk outreach, and non-API messaging workflows.

⚠️ Note: WhatsApp Business API (released May 2022) now provides an official method for bulk messaging. This repository is for educational/testing purposes only.

📬 Contact / Support

📱 GitHub: https://github.com/Bshadabkhan

💬 Feel free to reach out for help, fixes, or custom automation scripts.

⚠️ Important Note

WhatsApp Business released its official Cloud API in 2022 — allowing structured, scalable, and compliant messaging.

This script remains useful for:

One-time outreach

Personal / small-scale messaging

Non-commercial educational automation

Use cases where numbers aren’t saved

✅ Features

💬 Send bulk WhatsApp messages without saving contacts

📂 Reads contact numbers and messages from Excel

🤖 Fully automated using Selenium

🖥️ Uses WhatsApp Web (QR login required)

🔁 Auto-retry logic for failed messages

📝 Simple, clean Python script

📌 Option to extend for sending media (images, PDFs, etc.)

📦 Prerequisites

Install the following:

1️⃣ Python

Download Python 3.8+
👉 https://www.python.org/downloads

2️⃣ Google Chrome (v79 or above)

👉 https://chrome.google.com

3️⃣ Required Libraries

Run this in your terminal:

pip install pandas xlrd selenium webdriver_manager openpyxl

4️⃣ Excel File Structure

Create a file named Recipients data.xlsx with:

Contact	Message
9876543210	Hello! This is a test message
9123456789	Hello! This is a test message

(Message is usually taken from the first row.)

🔧 How It Works (Approach)

Clone this repository

Run the script:

python script.py


Browser opens WhatsApp Web

Scan QR Code

Press ENTER in terminal after login

Script automatically:

Reads contacts

Generates WhatsApp message URLs

Sends messages one-by-one

Browser closes automatically after completion

💡 You can modify the script to send images/documents.

🔐 Legal Disclaimer

This project is NOT affiliated with WhatsApp Inc.
This is an unofficial educational script.

⚠️ Use at your own risk

❌ Do NOT use for spam

🚫 Commercial usage is strictly prohibited

🔄 WhatsApp may update its HTML structure anytime (possible breakage)

🧠 Code
# Program to send bulk messages through WhatsApp web from an excel sheet without saving contact numbers
# Author @inforkgodara

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep
import pandas

excel_data = pandas.read_excel('Recipients data.xlsx', sheet_name='Recipients')

count = 0

driver = webdriver.Chrome(ChromeDriverManager().install())
driver.get('https://web.whatsapp.com')
input("Press ENTER after login into Whatsapp Web and your chats are visiable.")
for column in excel_data['Contact'].tolist():
    try:
        url = 'https://web.whatsapp.com/send?phone=' + str(excel_data['Contact'][count]) \
              + '&text=' + excel_data['Message'][0]
        sent = False

        driver.get(url)
        try:
            click_btn = WebDriverWait(driver, 35).until(
                EC.element_to_be_clickable((By.CLASS_NAME, '_3XKXx')))
        except Exception as e:
            print("Sorry message could not sent to " + str(excel_data['Contact'][count]))
        else:
            sleep(2)
            click_btn.click()
            sent = True
            sleep(5)
            print('Message sent to: ' + str(excel_data['Contact'][count]))
        count = count + 1

    except Exception as e:
        print('Failed to send message to ' + str(excel_data['Contact'][count]) + str(e))

driver.quit()
print("The script executed successfully.")

🛠️ Future Enhancements

Here are improvements you can implement:

⏳ Delay randomization (avoid ban risk)

🖼️ Support for images, video, PDF sending

📝 Per-contact dynamic messages

🚫 Auto-detection of invalid numbers

📊 Dashboard showing delivery stats

🤖 Integration with n8n for workflows

🔄 Headless browser mode

⭐ If You Like This Project…

Give it a ⭐ on GitHub to support future updates!
