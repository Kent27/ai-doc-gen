import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
import datetime
import json
import re
from .logging_utils import LOGS_DIR, formatter, clean_old_logs

# Create app logs directory
APP_LOGS_DIR = LOGS_DIR / "app"
APP_LOGS_DIR.mkdir(exist_ok=True)

def setup_app_logger():
    """
    Set up the main application logger with rotation and retention.
    
    Returns:
        The configured logger instance
    """
    # Get the app logger
    logger = logging.getLogger("app")
    
    # Only configure if not already configured
    if not logger.handlers:
        # Set up log file path
        log_file = APP_LOGS_DIR / "app.log"
        
        # Create a rotating file handler that rotates at midnight
        # and keeps logs for 30 days
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=30  # Keep logs for 30 days
        )
        
        # Set the formatter
        file_handler.setFormatter(formatter)
        
        # Add a console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Set level
        logger.setLevel(logging.INFO)
    
    return logger

def setup_request_logger():
    """
    Set up a logger specifically for HTTP requests with rotation and retention.
    
    Returns:
        The configured logger instance
    """
    # Get the request logger
    logger = logging.getLogger("app.requests")
    
    # Only configure if not already configured
    if not logger.handlers:
        # Set up log file path
        log_file = APP_LOGS_DIR / "requests.log"
        
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

# Initialize loggers
app_logger = setup_app_logger()
request_logger = setup_request_logger()

def compact_json(body_str: str) -> str:
    """
    Attempt to compact JSON strings in the body to make logs more efficient.
    If the body is not valid JSON, return it as is but with whitespace minimized.
    
    Args:
        body_str: The request body as a string
        
    Returns:
        Compacted string representation
    """
    # Skip empty bodies
    if not body_str or body_str.strip() == "":
        return ""
    
    try:
        # Try to parse as JSON
        if body_str.strip().startswith('{') or body_str.strip().startswith('['):
            # Parse and re-serialize without pretty printing
            data = json.loads(body_str)
            return json.dumps(data, separators=(',', ':'))
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If not JSON or parsing failed, just minimize whitespace
    # Replace multiple spaces with a single space
    compact_str = re.sub(r'\s+', ' ', body_str).strip()
    return compact_str

def log_request(method: str, url: str, body: str, status_code: int):
    """
    Log an HTTP request with all relevant details in a compact format.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        body: Request body as string
        status_code: Response status code
    """
    # Compact the body to save space
    compact_body = compact_json(body)
    
    # Truncate very long bodies
    if len(compact_body) > 1000:
        compact_body = compact_body[:997] + "..."
    
    # Create a compact log entry
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"{timestamp}|{method}|{url}|{status_code}|{compact_body}"
    
    # Log as a single line
    request_logger.info(log_entry)
    
    # Also log a more readable version at debug level for development
    app_logger.debug(f"Request: {method} {url} - Status: {status_code}")

# Run cleanup on import
clean_old_logs() 