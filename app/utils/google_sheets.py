import os
from datetime import datetime
from typing import Optional, Dict, Any
from .sheets_base import GoogleSheetsBase

class CustomerSheet(GoogleSheetsBase):
    def __init__(self):
        super().__init__(
            sheet_id=os.getenv('LOYALTY_SHEET_ID'),
            range_name="Sheet1!A2:E"  # A-E for the 5 columns
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

    async def insert_customer(self, phone_number: str, name: Optional[str] = None) -> bool:
        """Insert new customer with just name and phone number"""
        new_row = [
            name or '',        # Name
            phone_number,      # Phone Number
            '',               # Email (empty)
            '0',              # Loyalty Stamps (start with 0)
            ''                # Chat Status (empty)
        ]
        
        await self.append_values([new_row])
        return True

# Create singleton instance
customer_sheet = CustomerSheet()

# Expose functions at module level for backward compatibility
check_customer_exists = customer_sheet.check_customer_exists
update_customer_name = customer_sheet.update_customer_name
insert_customer = customer_sheet.insert_customer
