import os
import logging
from typing import Dict, Any
from ..services.whatsapp_service import WhatsAppService
from datetime import datetime

logger = logging.getLogger(__name__)
whatsapp_service = WhatsAppService()

async def alert_admin(message: str, severity: str = "info", context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Send an alert message to the admin's WhatsApp number
    
    Args:
        message: The alert message to send
        severity: Alert severity level (info, warning, error, critical)
        context: Additional context information to include in the alert
        
    Returns:
        Dict: Status and message
    """
    try:
        # Get admin phone number from environment variable
        admin_phone = os.getenv('ADMIN_WHATSAPP_NUMBER')
        if not admin_phone:
            logger.error("ADMIN_WHATSAPP_NUMBER not set in environment variables")
            return {
                "status": "error",
                "message": "Admin phone number not configured"
            }
        
        # Format the alert message with timestamp and severity
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"🚨 *ALERT* [{severity.upper()}] 🚨\n\n"
        formatted_message += f"*Time:* {timestamp}\n\n"
        formatted_message += f"*Message:* {message}\n"
        
        # Add context information if provided
        if context:
            formatted_message += "\n*Context:*\n"
            for key, value in context.items():
                formatted_message += f"- {key}: {value}\n"
        
        # Add severity-specific emoji
        if severity.lower() == "warning":
            formatted_message = "⚠️ " + formatted_message
        elif severity.lower() == "error":
            formatted_message = "❌ " + formatted_message
        elif severity.lower() == "critical":
            formatted_message = "🔥 " + formatted_message
        else:  # info
            formatted_message = "ℹ️ " + formatted_message
        
        # Send the message via WhatsApp
        response = await whatsapp_service.send_message(
            to=admin_phone,
            message=formatted_message
        )
        
        logger.info(f"Admin alert sent to {admin_phone}: {message}")
        return {
            "status": "success",
            "message": "Alert sent to admin successfully",
            "details": {
                "admin_phone": admin_phone,
                "severity": severity,
                "timestamp": timestamp
            }
        }
    except Exception as e:
        logger.error(f"Error sending admin alert: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to send alert: {str(e)}"
        } 