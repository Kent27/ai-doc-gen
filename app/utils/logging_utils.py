import os
import logging
from logging.handlers import TimedRotatingFileHandler
import datetime
import re
import shutil
import json
from pathlib import Path

# Base directory for all logs
LOGS_DIR = Path("app/logs")
WHATSAPP_LOGS_DIR = LOGS_DIR / "whatsapp"

# Ensure log directories exist
LOGS_DIR.mkdir(exist_ok=True)
WHATSAPP_LOGS_DIR.mkdir(exist_ok=True)

# Configure the base logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Create a formatter for consistent log formatting
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def get_phone_logger(phone_number: str) -> logging.Logger:
    """
    Get a logger for a specific phone number with proper rotation and retention.
    
    Args:
        phone_number: The phone number to create a logger for
        
    Returns:
        A configured logger instance for the phone number
    """
    # Sanitize phone number to use as filename (remove +, spaces, etc.)
    sanitized_phone = re.sub(r'[^\d]', '', phone_number)
    
    # Create a unique logger for this phone number
    logger = logging.getLogger(f"whatsapp.{sanitized_phone}")
    
    # Only add handlers if they don't exist yet
    if not logger.handlers:
        # Set up log file path
        log_file = WHATSAPP_LOGS_DIR / f"{sanitized_phone}.log"
        
        # Create a rotating file handler that rotates at midnight
        # and keeps logs for 30 days
        handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=30  # Keep logs for 30 days
        )
        
        # Set the formatter
        handler.setFormatter(formatter)
        
        # Add the handler to the logger
        logger.addHandler(handler)
        
        # Set level
        logger.setLevel(logging.INFO)
    
    return logger

def clean_old_logs(max_days: int = 30):
    """
    Clean logs older than max_days.
    This is a backup mechanism in addition to the backupCount in TimedRotatingFileHandler.
    
    Args:
        max_days: Maximum age of log files in days
    """
    current_time = datetime.datetime.now()
    cutoff_time = current_time - datetime.timedelta(days=max_days)
    
    # Check all files in the logs directory
    for log_dir in [LOGS_DIR, WHATSAPP_LOGS_DIR]:
        for log_file in log_dir.glob("*.log*"):
            # Get file modification time
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(log_file))
            
            # If file is older than cutoff, delete it
            if mod_time < cutoff_time:
                os.remove(log_file)
                print(f"Removed old log file: {log_file}")

def log_whatsapp_message(phone_number: str, message_type: str, message_data: dict, direction: str = "incoming"):
    """
    Log a WhatsApp message with all relevant details in a compact format.
    
    Args:
        phone_number: The phone number associated with the message
        message_type: Type of message (text, image, etc.)
        message_data: Dictionary containing message details
        direction: Direction of message ('incoming' or 'outgoing')
    """
    logger = get_phone_logger(phone_number)
    
    # Create a compact log entry
    timestamp = datetime.datetime.now().isoformat()
    
    # Compact the message data to save space
    try:
        # Serialize to compact JSON without whitespace
        compact_data = json.dumps(message_data, separators=(',', ':'))
    except (TypeError, ValueError):
        # If serialization fails, convert to string
        compact_data = str(message_data).replace('\n', ' ').replace('\r', '')
    
    # Format: TIMESTAMP|DIRECTION|TYPE|DATA
    log_entry = f"{timestamp}|{direction.upper()}|{message_type}|{compact_data}"
    
    # Log as a single line
    logger.info(log_entry)
    
    # Also log to the main application logger at debug level
    logging.getLogger("app").debug(f"WhatsApp {direction} message from {phone_number}: {message_type}")

# Run cleanup on import to ensure we don't accumulate old logs
clean_old_logs() 