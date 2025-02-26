# WhatsApp Logging System

This directory contains log files for the WhatsApp integration. The logging system is designed to:

1. Store logs per phone number
2. Automatically rotate logs daily
3. Retain logs for 30 days
4. Provide tools for log analysis and management

## Directory Structure

- `app/logs/` - Base directory for all logs
  - `app/` - Application-level logs
    - `app.log` - General application logs
    - `requests.log` - HTTP request logs
  - `whatsapp/` - WhatsApp-specific logs
    - `{phone_number}.log` - Logs for specific phone numbers

## Log Format

Each log entry includes:
- Timestamp
- Log level
- Message content

WhatsApp logs include structured data with:
- Direction (INCOMING/OUTGOING/SYSTEM)
- Message type (text, image, status, error, etc.)
- Message data (content, metadata, etc.)

## Log Management

You can use the `log_management.py` utility to manage and analyze logs:

```bash
# List all phone numbers with logs
python -m app.utils.log_management list

# Get logs for a specific phone number (last 7 days by default)
python -m app.utils.log_management get 1234567890 --days 7

# Search logs for a specific query
python -m app.utils.log_management search "error" --days 7

# Export logs for a specific phone number to a file
python -m app.utils.log_management export 1234567890 logs_export.json --days 30

# Force cleanup of old log files
python -m app.utils.log_management cleanup --days 30
```

## Log Rotation and Retention

Logs are automatically rotated at midnight each day and kept for 30 days. The rotation is handled by Python's `TimedRotatingFileHandler`.

Additionally, a cleanup function runs periodically to remove any log files older than 30 days as a backup mechanism.

## Programmatic Access

You can access the logging functionality in your code:

```python
# Log a WhatsApp message
from app.utils.logging_utils import log_whatsapp_message

log_whatsapp_message(
    phone_number="1234567890",
    message_type="text",
    message_data={"text": "Hello, world!"},
    direction="outgoing"
)

# Get the application logger
from app.utils.app_logger import app_logger

app_logger.info("Application event")
app_logger.error("Error occurred", exc_info=True)

# Log an HTTP request
from app.utils.app_logger import log_request

log_request(
    method="POST",
    url="https://example.com/api",
    body="request body",
    status_code=200
)
```

## Troubleshooting

If you encounter issues with the logging system:

1. Check that the log directories exist and are writable
2. Verify that the application has permission to create and modify files
3. Check disk space if logs are not being written
4. Use the cleanup utility if log files are consuming too much space 