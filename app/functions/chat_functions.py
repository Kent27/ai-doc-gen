import logging
from typing import Dict, Any
from ..utils.google_sheets import set_chat_status

logger = logging.getLogger(__name__)

async def enable_live_chat(phone_number: str) -> Dict[str, Any]:
    """
    Enable Live Chat mode for a customer
    
    Args:
        phone_number: The customer's phone number
        
    Returns:
        Dict: Status and message
    """
    try:
        # Normalize phone number format
        phone_number = phone_number.strip()
        
        success = await set_chat_status(phone_number, "Live Chat")
        
        if success:
            logger.info(f"Live Chat mode enabled for {phone_number}")
            return {
                "status": "success",
                "message": "Live Chat mode has been enabled. Your messages will now be handled by a human agent."
            }
        else:
            logger.error(f"Failed to enable Live Chat mode for {phone_number} - customer not found")
            return {
                "status": "error",
                "message": "Failed to enable Live Chat mode. Customer not found."
            }
    except Exception as e:
        logger.error(f"Error enabling Live Chat mode: {str(e)}")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }

async def disable_live_chat(phone_number: str) -> Dict[str, Any]:
    """
    Disable Live Chat mode for a customer
    
    Args:
        phone_number: The customer's phone number
        
    Returns:
        Dict: Status and message
    """
    try:
        # Normalize phone number format
        phone_number = phone_number.strip()
        
        success = await set_chat_status(phone_number, "")  # Empty string to disable Live Chat
        
        if success:
            logger.info(f"Live Chat mode disabled for {phone_number}")
            return {
                "status": "success",
                "message": "Live Chat mode has been disabled. Your messages will now be handled by the AI assistant."
            }
        else:
            logger.error(f"Failed to disable Live Chat mode for {phone_number} - customer not found")
            return {
                "status": "error",
                "message": "Failed to disable Live Chat mode. Customer not found."
            }
    except Exception as e:
        logger.error(f"Error disabling Live Chat mode: {str(e)}")
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        } 