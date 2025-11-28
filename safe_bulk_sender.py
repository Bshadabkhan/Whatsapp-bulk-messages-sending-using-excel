# safe_bulk_sender.py - Rate-Limited WhatsApp Sender
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List

class SafeRateLimiter:
    """Manages sending limits to avoid WhatsApp restrictions."""
    
    def __init__(self, max_per_hour=10, max_per_day=50):
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day
        self.stats_file = "sending_stats.json"
        self.stats = self.load_stats()
    
    def load_stats(self) -> Dict:
        """Load sending statistics from file."""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "daily_count": 0,
            "hourly_count": 0,
            "last_reset_day": datetime.now().strftime("%Y-%m-%d"),
            "last_reset_hour": datetime.now().strftime("%Y-%m-%d %H"),
            "sent_numbers": []
        }
    
    def save_stats(self):
        """Save statistics to file."""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def reset_counters_if_needed(self):
        """Reset counters if time periods have passed."""
        now = datetime.now()
        current_day = now.strftime("%Y-%m-%d")
        current_hour = now.strftime("%Y-%m-%d %H")
        
        # Reset daily counter
        if self.stats["last_reset_day"] != current_day:
            self.stats["daily_count"] = 0
            self.stats["last_reset_day"] = current_day
            self.stats["sent_numbers"] = []  # Reset daily sent numbers
        
        # Reset hourly counter
        if self.stats["last_reset_hour"] != current_hour:
            self.stats["hourly_count"] = 0
            self.stats["last_reset_hour"] = current_hour
    
    def can_send_message(self, phone_number: str = None) -> tuple[bool, str]:
        """Check if we can send a message now."""
        self.reset_counters_if_needed()
        
        # Check daily limit
        if self.stats["daily_count"] >= self.max_per_day:
            return False, f"Daily limit reached ({self.max_per_day} messages)"
        
        # Check hourly limit
        if self.stats["hourly_count"] >= self.max_per_hour:
            return False, f"Hourly limit reached ({self.max_per_hour} messages)"
        
        # Check if already sent to this number today
        if phone_number and phone_number in self.stats["sent_numbers"]:
            return False, f"Already sent to {phone_number} today"
        
        return True, "OK"
    
    def record_sent_message(self, phone_number: str):
        """Record that a message was sent."""
        self.stats["daily_count"] += 1
        self.stats["hourly_count"] += 1
        if phone_number:
            self.stats["sent_numbers"].append(phone_number)
        self.save_stats()
    
    def get_time_until_next_send(self) -> int:
        """Get seconds until next message can be sent."""
        can_send, reason = self.can_send_message()
        if can_send:
            return 0
        
        if "hourly" in reason.lower():
            # Wait until next hour
            now = datetime.now()
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            return int((next_hour - now).total_seconds())
        
        if "daily" in reason.lower():
            # Wait until next day
            now = datetime.now()
            next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            return int((next_day - now).total_seconds())
        
        return 0
    
    def get_stats_summary(self) -> str:
        """Get current statistics summary."""
        self.reset_counters_if_needed()
        return (
            f"Today: {self.stats['daily_count']}/{self.max_per_day} messages | "
            f"This hour: {self.stats['hourly_count']}/{self.max_per_hour} messages"
        )

# Updated Config class with safety limits
class SafeConfig:
    EXCEL_FILE = "ExcelData.xlsx"
    USER_DATA_DIR = os.path.abspath("./User_Data")
    PORTABLE_CHROME = r"C:\Users\User\Downloads\chrome-win64\chrome.exe"
    WAIT_LOGIN_SECONDS = 60
    MESSAGE_DELAY_SECONDS = 8  # Increased delay
    MAX_RETRIES = 2
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    LOG_FILE = "whatsapp_sender.log"
    
    # Safety limits
    MAX_MESSAGES_PER_HOUR = 10
    MAX_MESSAGES_PER_DAY = 50
    MIN_DELAY_BETWEEN_MESSAGES = 5  # Minimum seconds between messages
    MAX_DELAY_BETWEEN_MESSAGES = 15  # Maximum seconds between messages

def calculate_dynamic_delay(message_count: int) -> int:
    """Calculate delay based on number of messages sent."""
    base_delay = SafeConfig.MIN_DELAY_BETWEEN_MESSAGES
    
    # Increase delay as we send more messages
    if message_count < 10:
        return base_delay
    elif message_count < 20:
        return base_delay + 3
    elif message_count < 30:
        return base_delay + 6
    else:
        return SafeConfig.MAX_DELAY_BETWEEN_MESSAGES

def estimate_completion_time(remaining_messages: int, rate_limiter: SafeRateLimiter) -> str:
    """Estimate when all messages will be sent."""
    messages_today = rate_limiter.stats["daily_count"]
    max_per_day = rate_limiter.max_per_day
    max_per_hour = rate_limiter.max_per_hour
    
    if remaining_messages <= 0:
        return "Complete"
    
    # Can we finish today?
    remaining_today = max_per_day - messages_today
    if remaining_messages <= remaining_today:
        # Estimate based on hourly rate
        hours_needed = (remaining_messages / max_per_hour)
        if hours_needed < 1:
            return f"~{int(hours_needed * 60)} minutes"
        else:
            return f"~{hours_needed:.1f} hours"
    else:
        # Need multiple days
        days_needed = (remaining_messages / max_per_day)
        return f"~{days_needed:.1f} days"

# Example usage function to show how to integrate with your main script
def safe_sending_example():
    """Example of how to use the rate limiter."""
    rate_limiter = SafeRateLimiter(
        max_per_hour=SafeConfig.MAX_MESSAGES_PER_HOUR,
        max_per_day=SafeConfig.MAX_MESSAGES_PER_DAY
    )
    
    print("=== WhatsApp Safe Bulk Sender ===")
    print(f"Limits: {rate_limiter.max_per_hour}/hour, {rate_limiter.max_per_day}/day")
    print(f"Current status: {rate_limiter.get_stats_summary()}")
    
    # Example phone numbers (replace with your actual data)
    phone_numbers = ["1234567890", "0987654321", "5555555555"]
    
    for i, phone in enumerate(phone_numbers):
        # Check if we can send
        can_send, reason = rate_limiter.can_send_message(phone)
        
        if not can_send:
            wait_time = rate_limiter.get_time_until_next_send()
            if wait_time > 0:
                print(f"Rate limit reached: {reason}")
                print(f"Waiting {wait_time//3600}h {(wait_time%3600)//60}m before continuing...")
                # In real implementation, you might want to schedule for later
                break
            else:
                print(f"Skipping {phone}: {reason}")
                continue
        
        # Simulate sending message
        print(f"Sending to {phone}...")
        
        # Your actual message sending code here
        # success = your_whatsapp_sender.send_message(phone, image_path, caption)
        success = True  # Simulated success
        
        if success:
            rate_limiter.record_sent_message(phone)
            print(f"✓ Sent to {phone}")
        else:
            print(f"✗ Failed to send to {phone}")
        
        # Dynamic delay
        delay = calculate_dynamic_delay(rate_limiter.stats["daily_count"])
        remaining = len(phone_numbers) - (i + 1)
        completion_time = estimate_completion_time(remaining, rate_limiter)
        
        print(f"Status: {rate_limiter.get_stats_summary()}")
        print(f"Estimated completion: {completion_time}")
        
        if remaining > 0:
            print(f"Waiting {delay} seconds before next message...")
            time.sleep(delay)
    
    print("\nSending session complete!")
    print(f"Final stats: {rate_limiter.get_stats_summary()}")

if __name__ == "__main__":
    safe_sending_example()