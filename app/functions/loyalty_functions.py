import os
from ..utils.sheets_base import GoogleSheetsBase

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

# Create singleton instance
loyalty_sheet = LoyaltySheet()

# Expose function at module level for backward compatibility
get_stamp_loyalty = loyalty_sheet.get_stamp_loyalty
