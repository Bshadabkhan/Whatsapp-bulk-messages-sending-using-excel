# app.py - Improved WhatsApp Bulk Sender
import os
import time
import sys
import subprocess
import pandas as pd
import logging
from typing import Optional,Tuple
from selenium import webdriver
from selenium.common.exceptions import (TimeoutException,NoSuchElementException, ElementNotInteractableException)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ===== Configuration =====
class Config:
    EXCEL_FILE = "ExcelData.xlsx"
    USER_DATA_DIR = os.path.abspath("./User_Data")
    PORTABLE_CHROME = r"C:\Users\User\Downloads\chrome-win64\chrome.exe"
    WAIT_LOGIN_SECONDS = 60
    MESSAGE_DELAY_SECONDS = 3  # Delay between messages to avoid being flagged
    MAX_RETRIES = 2
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    LOG_FILE = "whatsapp_sender.log"

# ===== Logging Setup =====
def setup_logging():
    """Configure logging to both file and console."""
    # Configure file handler with UTF-8 encoding
    file_handler = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Configure console handler with UTF-8 encoding for Windows
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Set formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Set console encoding to UTF-8 for Windows
    if sys.platform.startswith('win'):
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        except:
            pass  # Fallback to default encoding
    
    return logger

# ===== Utility Functions =====
def validate_phone_number(phone: str) -> Optional[str]:
    """Validate and clean phone number."""
    if pd.isna(phone):
        return None
    
    cleaned = str(phone).strip().replace("+", "").replace(" ", "").replace("-", "")
    
    # Basic validation: should be digits and reasonable length
    if not cleaned.isdigit() or len(cleaned) < 10 or len(cleaned) > 15:
        return None
    
    return cleaned

def validate_image_path(image_path: str) -> bool:
    """Validate image file exists and has supported format."""
    if pd.isna(image_path):
        return False
    
    image_path = str(image_path).strip()
    
    if not os.path.isfile(image_path):
        return False
    
    file_ext = os.path.splitext(image_path.lower())[1]
    return file_ext in Config.SUPPORTED_IMAGE_FORMATS

def get_chrome_version(chrome_path: str) -> Optional[str]:
    """Return chrome version string if binary exists and is runnable."""
    if not chrome_path or not os.path.isfile(chrome_path):
        return None
    
    try:
        result = subprocess.run(
            [chrome_path, "--version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    
    return None

# ===== WebDriver Management =====
class WhatsAppDriver:
    def __init__(self, logger: logging.Logger):
        self.driver = None
        self.logger = logger
    
    def start_driver(self, use_portable: bool = True) -> webdriver.Chrome:
        """Initialize Chrome WebDriver with optimal settings."""
        chrome_options = Options()
        
        # Essential options
        chrome_options.add_argument(f"--user-data-dir={Config.USER_DATA_DIR}")
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-gpu-sandbox")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-gpu-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use portable Chrome if available and requested
        if use_portable and os.path.isfile(Config.PORTABLE_CHROME):
            chrome_options.binary_location = Config.PORTABLE_CHROME
            version = get_chrome_version(Config.PORTABLE_CHROME)
            self.logger.info(f"Using portable Chrome: {Config.PORTABLE_CHROME}")
            if version:
                self.logger.info(f"Chrome version: {version}")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute script to hide automation indicators
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            return self.driver
        except Exception as e:
            self.logger.error(f"Failed to start WebDriver: {e}")
            raise
    
    def wait_for_whatsapp_login(self) -> bool:
        """Wait for WhatsApp Web to load and user to login."""
        self.driver.get("https://web.whatsapp.com")
        self.logger.info("WhatsApp Web opened. Waiting for login...")
        
        try:
            # Wait for either QR code or main interface
            WebDriverWait(self.driver, Config.WAIT_LOGIN_SECONDS).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "canvas[aria-label='Scan me!']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='search']")),
                    EC.presence_of_element_located((By.XPATH, "//div[@role='textbox'][@data-lexical-editor='true']"))
                )
            )
            self.logger.info("WhatsApp Web interface detected")
            return True
        except TimeoutException:
            self.logger.warning("WhatsApp Web login timeout - may require manual intervention")
            return False
    
    def click_attach_button(self) -> bool:
        """Try multiple strategies to click the attach button."""
        # First, let's debug what's currently available
        self.debug_available_elements()
        
        # Updated selectors for current WhatsApp Web (August 2025)
        attach_selectors = [
            # Latest WhatsApp selectors
            "//div[@aria-label='Attach']",
            "//button[@aria-label='Attach']",
            "//div[@title='Attach']",
            "//button[@title='Attach']",
            
            # Icon-based selectors
            "//span[@data-icon='plus']/..",
            "//span[@data-icon='attach-menu-plus']/..",
            "//span[@data-icon='clip']/..",
            "//div[contains(@class, 'attach') or contains(@aria-label, 'attach')]",
            
            # Role-based selectors
            "//div[@role='button'][contains(@aria-label, 'Attach')]",
            "//button[@role='button'][contains(@aria-label, 'Attach')]",
            
            # Fallback selectors
            "//div[@role='button'][.//span[contains(@data-icon, 'plus')]]",
            "//div[@role='button'][.//span[contains(@data-icon, 'attach')]]",
            "//div[@role='button'][.//span[contains(@data-icon, 'clip')]]",
            
            # Generic plus button (often used for attach)
            "//div[contains(@class, 'plus') or contains(@aria-label, 'plus')]",
            "//button[contains(@class, 'plus') or contains(@aria-label, 'plus')]"
        ]
        
        for i, selector in enumerate(attach_selectors):
            try:
                self.logger.debug(f"Trying attach selector {i+1}: {selector}")
                button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                
                # Try different click methods
                try:
                    button.click()
                    self.logger.debug(f"Attach button clicked with regular click (selector {i+1})")
                except:
                    try:
                        self.driver.execute_script("arguments[0].click();", button)
                        self.logger.debug(f"Attach button clicked with JS click (selector {i+1})")
                    except:
                        continue
                
                # Wait a moment and check if attach menu appeared
                time.sleep(1)
                try:
                    # Look for photo/document options that appear after clicking attach
                    WebDriverWait(self.driver, 3).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.XPATH, "//input[@type='file']")),
                            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Photos')]")),
                            EC.presence_of_element_located((By.XPATH, "//div[contains(@aria-label, 'Photos')]"))
                        )
                    )
                    self.logger.debug("Attach menu opened successfully")
                    return True
                except TimeoutException:
                    self.logger.debug("Attach menu didn't appear, trying next selector")
                    continue
                    
            except (TimeoutException, NoSuchElementException, ElementNotInteractableException) as e:
                self.logger.debug(f"Selector {i+1} failed: {e}")
                continue
        
        self.logger.error("Could not find or click attach button")
        return False
    
    def debug_available_elements(self):
        """Debug helper to see what elements are available on the page."""
        try:
            # Look for common button patterns
            buttons = self.driver.find_elements(By.XPATH, "//div[@role='button'] | //button")
            self.logger.debug(f"Found {len(buttons)} buttons on page")
            
            # Look for elements with attach-related attributes
            attach_elements = self.driver.find_elements(By.XPATH, 
                "//*[contains(@aria-label, 'ttach') or contains(@title, 'ttach') or contains(@aria-label, 'Plus')]")
            
            for i, elem in enumerate(attach_elements[:5]):  # Log first 5
                try:
                    tag = elem.tag_name
                    aria_label = elem.get_attribute('aria-label') or 'None'
                    title = elem.get_attribute('title') or 'None'
                    class_name = elem.get_attribute('class') or 'None'
                    self.logger.debug(f"Attach element {i+1}: <{tag}> aria-label='{aria_label}' title='{title}' class='{class_name}'")
                except Exception:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Debug failed: {e}")
    
    def upload_image(self, image_path: str) -> bool:
        """Upload image file through file input."""
        try:
            # First try to click on Photos/Images option if attach menu is open
            photo_selectors = [
                "//div[contains(@aria-label, 'Photos') or contains(text(), 'Photos')]",
                "//div[contains(@aria-label, 'Images') or contains(text(), 'Images')]",
                "//span[contains(text(), 'Photos & Videos')]",
                "//div[@title='Photos & Videos']"
            ]
            
            photo_clicked = False
            for selector in photo_selectors:
                try:
                    photo_option = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    photo_option.click()
                    photo_clicked = True
                    self.logger.debug("Photos option clicked")
                    break
                except:
                    continue
            
            if not photo_clicked:
                self.logger.debug("No photos option found, looking for direct file input")
            
            time.sleep(1)
            
            # Find file input element
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            
            file_input = None
            for inp in file_inputs:
                accept_attr = inp.get_attribute("accept") or ""
                # Look for inputs that accept images
                if "image" in accept_attr or "/*" in accept_attr or not accept_attr:
                    file_input = inp
                    self.logger.debug(f"Found file input with accept='{accept_attr}'")
                    break
            
            if not file_input:
                raise NoSuchElementException("No suitable file input found")
            
            # Upload file
            absolute_path = os.path.abspath(image_path)
            file_input.send_keys(absolute_path)
            self.logger.debug(f"Image uploaded: {image_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload image: {e}")
            return False
    
    def add_caption_and_send(self, caption: str) -> bool:
        """Add caption and send the message."""
        try:
            # Wait for caption box to appear
            caption_selectors = [
                "//div[@contenteditable='true'][@data-lexical-editor='true']",
                "//div[@contenteditable='true'][contains(@aria-label, 'caption')]",
                "//div[@contenteditable='true'][@data-tab='10']"
            ]
            
            caption_box = None
            for selector in caption_selectors:
                try:
                    caption_box = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not caption_box:
                raise NoSuchElementException("Caption box not found")
            
            # Add caption if provided
            caption_box.click()
            if caption and caption.strip():
                caption_box.send_keys(caption.strip())
            
            time.sleep(1)
            
            # Try to find and click send button
            send_selectors = [
                "//span[@data-icon='send']/..",
                "//div[@aria-label='Send']",
                "//button[@aria-label='Send']"
            ]
            
            sent = False
            for selector in send_selectors:
                try:
                    send_btn = self.driver.find_element(By.XPATH, selector)
                    send_btn.click()
                    sent = True
                    break
                except NoSuchElementException:
                    continue
            
            # Fallback: use Enter key
            if not sent:
                caption_box.send_keys(Keys.ENTER)
            
            self.logger.debug("Message sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    def send_message_to_contact(self, phone: str, image_path: str, caption: str) -> bool:
        """Send image with caption to a specific phone number."""
        try:
            # Navigate to chat
            chat_url = f"https://web.whatsapp.com/send?phone={phone}&app_absent=0"
            self.driver.get(chat_url)
            
            # Wait for chat to load
            WebDriverWait(self.driver, 30).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//div[@role='button']")),
                    EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                )
            )
            
            time.sleep(2)  # Allow UI to stabilize
            
            # Click attach button
            if not self.click_attach_button():
                return False
            
            time.sleep(1)
            
            # Upload image
            if not self.upload_image(image_path):
                return False
            
            time.sleep(2)  # Wait for image to process
            
            # Add caption and send
            if not self.add_caption_and_send(caption):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message to {phone}: {e}")
            return False
    
    def quit(self):
        """Safely quit the driver."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")

# ===== Main Application =====
class WhatsAppBulkSender:
    def __init__(self):
        self.logger = setup_logging()
        self.driver_manager = WhatsAppDriver(self.logger)
        self.stats = {
            'total': 0,
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def load_data(self) -> pd.DataFrame:
        """Load and validate Excel data."""
        if not os.path.isfile(Config.EXCEL_FILE):
            raise FileNotFoundError(f"Excel file not found: {Config.EXCEL_FILE}")
        
        try:
            df = pd.read_excel(Config.EXCEL_FILE)
            self.logger.info(f"Loaded {len(df)} rows from {Config.EXCEL_FILE}")
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {e}")
        
        # Validate required columns
        required_cols = {'PhoneNumber', 'Caption', 'ImagePath'}
        if not required_cols.issubset(set(df.columns)):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Missing required columns: {missing}")
        
        return df
    
    def validate_row(self, row: pd.Series, index: int) -> Tuple[Optional[str], Optional[str], bool]:
        """Validate a single row and return cleaned data."""
        phone = validate_phone_number(row['PhoneNumber'])
        if not phone:
            self.logger.warning(f"Row {index + 1}: Invalid phone number: {row['PhoneNumber']}")
            return None, None, False
        
        image_path = str(row['ImagePath']).strip() if not pd.isna(row['ImagePath']) else ""
        if not validate_image_path(image_path):
            self.logger.warning(f"Row {index + 1}: Invalid image path: {image_path}")
            return None, None, False
        
        caption = str(row['Caption']) if not pd.isna(row['Caption']) else ""
        
        return phone, caption, True
    
    def run(self):
        """Main execution function."""
        try:
            # Load data
            df = self.load_data()
            self.stats['total'] = len(df)
            
            # Start WebDriver
            self.logger.info("Starting Chrome WebDriver...")
            try:
                self.driver_manager.start_driver(use_portable=True)
            except Exception as e:
                self.logger.warning(f"Portable Chrome failed: {e}")
                self.logger.info("Falling back to system Chrome...")
                self.driver_manager.start_driver(use_portable=False)
            
            # Login to WhatsApp
            if not self.driver_manager.wait_for_whatsapp_login():
                self.logger.error("WhatsApp login failed or timed out")
                return
            
            input("\nAfter logging in and seeing your chats, press ENTER to start sending messages...")
            
            # Process each row
            for index, row in df.iterrows():
                phone, caption, is_valid = self.validate_row(row, index)
                
                if not is_valid:
                    self.stats['skipped'] += 1
                    continue
                
                image_path = str(row['ImagePath']).strip()
                
                self.logger.info(f"Sending message {index + 1}/{len(df)} to {phone}")
                
                # Attempt to send message with retries
                success = False
                for attempt in range(Config.MAX_RETRIES):
                    if attempt > 0:
                        self.logger.info(f"Retry attempt {attempt + 1} for {phone}")
                        time.sleep(2)
                    
                    if self.driver_manager.send_message_to_contact(phone, image_path, caption):
                        success = True
                        break
                
                if success:
                    self.stats['sent'] += 1
                    self.logger.info(f"[SUCCESS] Message sent to {phone}")
                else:
                    self.stats['failed'] += 1
                    self.logger.error(f"[FAILED] Could not send to {phone} after {Config.MAX_RETRIES} attempts")
                
                # Delay between messages
                if index < len(df) - 1:  # Don't delay after last message
                    self.logger.info(f"Waiting {Config.MESSAGE_DELAY_SECONDS} seconds before next message...")
                    time.sleep(Config.MESSAGE_DELAY_SECONDS)
        
        except KeyboardInterrupt:
            self.logger.info("Process interrupted by user")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        finally:
            # Cleanup and show stats
            self.cleanup()
            self.show_stats()
    
    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up...")
        time.sleep(3)  # Allow final message to send
        self.driver_manager.quit()
    
    def show_stats(self):
        """Display final statistics."""
        self.logger.info("=== FINAL STATISTICS ===")
        self.logger.info(f"Total contacts: {self.stats['total']}")
        self.logger.info(f"Successfully sent: {self.stats['sent']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped (invalid): {self.stats['skipped']}")
        self.logger.info(f"Success rate: {(self.stats['sent']/max(1, self.stats['total']))*100:.1f}%")
        
# ===== Entry Point =====
if __name__ == "__main__":
    app = WhatsAppBulkSender()
    app.run()