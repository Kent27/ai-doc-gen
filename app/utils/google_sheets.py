import os
from datetime import datetime
from typing import Optional, Dict, Any
from .sheets_base import GoogleSheetsBase
import logging

logger = logging.getLogger(__name__)

class CustomerSheet(GoogleSheetsBase):
    def __init__(self):
        super().__init__(
            sheet_id=os.getenv('LOYALTY_SHEET_ID'),
            range_name="Sheet1!A2:F"  # A-F for the 6 columns
        )

    async def check_customer_exists(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Check if customer exists in Google Sheets"""
        values = await self.get_values()
        if not values:
            return None
            
        for row_num, row in enumerate(values):
            # Phone number is in column B (index 1)
            if len(row) > 1 and row[1] == phone_number:
                return {
                    'name': row[0],  # Name (Column A)
                    'phone': row[1],  # Phone Number (Column B)
                    'email': row[2] if len(row) > 2 else None,  # Email (Column C)
                    'stamps': row[3] if len(row) > 3 else '0',  # Loyalty Stamps (Column D)
                    'chat_status': row[4] if len(row) > 4 else None,  # Chat Status (Column E)
                    'thread_id': row[5] if len(row) > 5 else None,  # Thread ID (Column F)
                    'row_number': row_num + 2  # Add 2 because data starts from row 2
                }
                
        return None

    async def update_customer_name(self, phone_number: str, new_name: str) -> bool:
        """Update customer name in Google Sheets"""
        customer = await self.check_customer_exists(phone_number)
        if not customer:
            return False
            
        range_name = f'Sheet1!A{customer["row_number"]}'
        values = [[new_name]]
        
        await self.update_values(range_name, values)
        return True

    async def update_customer(self, customer, data: dict) -> bool:
        """Update customer data in Google Sheets"""
        try:
            # Instead of updating the entire row at once, update specific cells
            # This prevents race conditions when multiple processes update different parts of the same row
            
            # Update name if provided
            if 'name' in data and data['name'] != customer.get('name'):
                await self.update_values(
                    f'Sheet1!A{customer["row_number"]}',
                    [[data['name']]]
                )
            
            # Update chat_status if provided
            if 'chat_status' in data and data['chat_status'] != customer.get('chat_status'):
                await self.update_values(
                    f'Sheet1!E{customer["row_number"]}',
                    [[data['chat_status']]]
                )
            
            # Update thread_id if provided
            if 'thread_id' in data and data['thread_id'] != customer.get('thread_id'):
                await self.update_values(
                    f'Sheet1!F{customer["row_number"]}',
                    [[data['thread_id']]]
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating customer: {str(e)}")
            raise

    async def update_thread_id(self, customer, thread_id: str) -> bool:
        """Update only the thread_id for a customer
        
        This is a specialized function to avoid race conditions when
        multiple processes are updating different parts of the same customer record.
        """
        try:
            if not thread_id or thread_id == customer.get('thread_id'):
                return True  # No change needed
                
            # Update only the thread_id cell (Column F)
            await self.update_values(
                f'Sheet1!F{customer["row_number"]}',
                [[thread_id]]
            )
            return True
            
        except Exception as e:
            logger.error(f"Error updating thread_id: {str(e)}")
            raise

    async def insert_customer(self, data: dict) -> None:
        """Insert new customer with all fields"""
        try:
            new_row = [
                data['name'],
                data['phone'],
                '',               # Email (empty)
                '0',              # Loyalty Stamps (start with 0)
                data.get('chat_status', ''),  # Chat Status (empty or provided)
                data['thread_id']
            ]
            # Explicitly specify the range to ensure we start from column A
            await self.append_values([new_row], range_name="Sheet1!A1")
        except Exception as e:
            logger.error(f"Error inserting customer: {str(e)}")
            raise

    async def set_chat_status(self, phone_number: str, status: str) -> bool:
        """
        Set the chat status for a customer
        
        Args:
            phone_number: The customer's phone number
            status: The status to set (e.g., "Live Chat")
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            customer = await self.check_customer_exists(phone_number)
            if not customer:
                return False
                
            # Update just the chat status column (Column E)
            range_name = f'Sheet1!E{customer["row_number"]}'
            values = [[status]]
            
            await self.update_values(range_name, values)
            return True
            
        except Exception as e:
            logger.error(f"Error setting chat status: {str(e)}")
            return False

# Create singleton instance
customer_sheet = CustomerSheet()

# Expose functions at module level for backward compatibility
check_customer_exists = customer_sheet.check_customer_exists
update_customer_name = customer_sheet.update_customer_name
insert_customer = customer_sheet.insert_customer
update_customer = customer_sheet.update_customer
update_thread_id = customer_sheet.update_thread_id
set_chat_status = customer_sheet.set_chat_status
