# Live Chat Mode

This document explains how to use the "Live Chat" mode feature, which allows you to bypass AI processing for specific customers.

## Overview

When a customer's status is set to "Live Chat" in the Google Sheets, the system will:

1. Skip AI processing for incoming WhatsApp messages
2. Log the message but not send it to the AI assistant
3. Allow human operators to handle the conversation directly

This is useful for:
- Handling complex customer issues that require human intervention
- Providing personalized service for VIP customers
- Troubleshooting when the AI is not providing satisfactory responses

## How to Use

### Setting a Customer to Live Chat Mode

#### Using the API

You can set a customer to Live Chat mode using the API endpoint:

```bash
curl -X POST "http://your-server/whatsapp/set-chat-status" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "6281234567890",
    "status": "Live Chat"
  }'
```

#### Using the Command Line Utility

You can also use the command line utility:

```bash
# Set a customer to Live Chat mode
python -m app.utils.manage_chat_status set 6281234567890 "Live Chat"

# Check a customer's current status
python -m app.utils.manage_chat_status get 6281234567890

# Clear a customer's status (re-enable AI processing)
python -m app.utils.manage_chat_status clear 6281234567890
```

#### Directly in Google Sheets

You can also set the status directly in the Google Sheets:
1. Open the Customers Google Sheet
2. Find the customer's row
3. In the "Status" column (Column E), enter "Live Chat"

### Handling Live Chat Conversations

When a customer is in Live Chat mode:

1. Their messages will still be logged in the system
2. You'll need to respond to them manually through your WhatsApp Business interface
3. The system will not send any automated AI responses

### Returning to AI Mode

To return a customer to normal AI processing:

1. Clear their status using the API, command line utility, or directly in the Google Sheet
2. Verify the status has been cleared by checking with the `get` command

## Logging

All messages from customers in Live Chat mode are still logged in the system. You can view these logs using the logging tools:

```bash
# View logs for a specific phone number
python -m app.utils.log_management get 6281234567890 --days 7
```

The logs will include a system message indicating that AI processing was skipped due to Live Chat mode.

## Troubleshooting

If you're having issues with the Live Chat mode:

1. Verify the customer's status is correctly set to "Live Chat" (exact spelling and capitalization)
2. Check the logs to ensure the system is recognizing the Live Chat status
3. Make sure the Google Sheets integration is working properly

If you need to quickly disable Live Chat mode for all customers, you can clear the entire Status column in the Google Sheet. 