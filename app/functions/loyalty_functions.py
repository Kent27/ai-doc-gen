import os
from ..utils.sheets_base import GoogleSheetsBase
from typing import Dict, List, Optional
from datetime import datetime

class LoyaltySheet(GoogleSheetsBase):
    def __init__(self):
        super().__init__(
            sheet_id=os.getenv('LOYALTY_SHEET_ID'),
            range_name='Sheet1!A2:F'
        )

    async def get_stamp_loyalty(self, nomor_telepon: str) -> dict:
        """Get loyalty stamp information for a customer by phone number"""
        try:
            values = await self.get_values()
            for row in values:
                if len(row) > 1 and row[1] == nomor_telepon:
                    return {
                        "status": "success",
                        "data": {
                            "nama": row[0],
                            "nomor_telepon": row[1],
                            "jumlah_stamp": row[3],
                        }
                    }
            
            return {
                "status": "not_found",
                "message": "Mohon maaf, nomor telepon tidak terdaftar dalam program stamp loyalti"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Terjadi kesalahan: {str(e)}"
            }

    async def add_stamps(self, phone_number: str, stamps_to_add: int) -> bool:
        """Add loyalty stamps to specific customer's account"""
        print(f"Adding {stamps_to_add} stamps to {phone_number}")
        try:
            values = await self.get_values()
            if not values:
                return False
            
            # Find the customer's row
            for row_index, row in enumerate(values):
                if len(row) > 1 and row[1] == phone_number:
                    current_stamps = int(row[3]) if len(row) > 3 else 0
                    new_stamps = current_stamps + stamps_to_add
                    
                    # Update stamps in the loyalty sheet (row_index + 2 because data starts at row 2)
                    await self.update_values(
                        f'Sheet1!D{row_index + 2}',
                        [[str(new_stamps)]]
                    )
                    return True
            
            return False  # Customer not found
        
        except Exception as e:
            print(f"Error adding stamps: {str(e)}")
            return False

# Create singleton instance
loyalty_sheet = LoyaltySheet()

# Expose function at module level for backward compatibility
get_stamp_loyalty = loyalty_sheet.get_stamp_loyalty

class InvoiceSheet(GoogleSheetsBase):
    def __init__(self):
        super().__init__(
            sheet_id="1n0mHlQRbFOVSoykTwUuGIFb9AFbvV9XEHeiJM69Wo5s",
            range_name='Sheet1!A2:E'  # A-E for ID, Total, Claimed, Claimed By, Claimed At columns
        )

    async def process_invoices(self, **kwargs) -> Dict:
        """Process invoices and update loyalty stamps"""
        try:
            # Convert kwargs to the expected format
            invoice_data = {
                "invoices": kwargs.get("invoices", []),
                "metadata": kwargs.get("metadata", {})
            }
            
            invoices = invoice_data["invoices"]
            phone_number = invoice_data["metadata"].get("phone_number")
            customer_name = invoice_data["metadata"].get("customer_name", "Unknown")
            
            if not invoices:
                return {
                    "status": "error",
                    "message": "Format invoice tidak valid"
                }

            if not phone_number:
                return {
                    "status": "error",
                    "message": "Nomor telepon diperlukan dalam metadata"
                }

            # Get current invoice data
            values = await self.get_values()
            existing_invoices = {
                row[0]: {
                    "total": row[1], 
                    "claimed": row[2].lower() == "true",
                    "claimed_by": row[3] if len(row) > 3 else None,
                    "claimed_at": row[4] if len(row) > 4 else None
                } 
                for row in values if len(row) >= 3
            }
            
            total_amount = 0
            processed_invoices = []
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for invoice in invoices:
                invoice_id = invoice.get("id")
                invoice_total = float(invoice.get("total", 0))
                
                if not invoice_id or not invoice_total:
                    continue
                
                if invoice_id not in existing_invoices:
                    # Add new invoice with claim details
                    await self.append_values([
                        [
                            invoice_id, 
                            str(invoice_total), 
                            "true",
                            f"{customer_name} ({phone_number})",
                            current_time
                        ]
                    ])
                    total_amount += invoice_total
                    processed_invoices.append(invoice_id)
                elif not existing_invoices[invoice_id]["claimed"]:
                    # Update existing unclaimed invoice
                    row_num = next(i for i, row in enumerate(values) if row[0] == invoice_id) + 2
                    await self.update_values(
                        f'Sheet1!C{row_num}:E{row_num}',
                        [[
                            "true",
                            f"{customer_name} ({phone_number})",
                            current_time
                        ]]
                    )
                    total_amount += invoice_total
                    processed_invoices.append(invoice_id)

            # Calculate and add loyalty stamps
            stamps_added = 0
            if total_amount > 0:
                stamps_to_add = int(total_amount // 50000)
                if stamps_to_add > 0:
                    if await loyalty_sheet.add_stamps(phone_number, stamps_to_add):
                        stamps_added = stamps_to_add

            return {
                "status": "success",
                "processed_invoices": processed_invoices,
                "total_amount": total_amount,
                "stamps_added": stamps_added,
                "message": f"Berhasil memproses {len(processed_invoices)} invoice dan menambahkan {stamps_added} stamp"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Terjadi kesalahan saat memproses invoice: {str(e)}"
            }

# Create singleton instance
invoice_sheet = InvoiceSheet()

# Expose function at module level
process_invoices = invoice_sheet.process_invoices
