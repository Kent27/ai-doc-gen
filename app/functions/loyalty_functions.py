import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SHEET_ID = os.getenv('LOYALTY_SHEET_ID')
RANGE = 'Sheet1!A2:F'  # Assuming data starts from row 2

def get_credentials():
    """Get credentials from environment or file"""
    sheet_id = os.getenv('LOYALTY_SHEET_ID')
    print(f"Debug - Sheet ID: {sheet_id}") 
    print(f"Debug - OPENAI key: {os.getenv('OPENAI_API_KEY')}")
    # google_creds = os.getenv('GOOGLE_CREDENTIALS')
    # if google_creds:
    #     credentials_dict = json.loads(google_creds)
    #     return service_account.Credentials.from_service_account_info(
    #         credentials_dict,
    #         scopes=SCOPES
    #     )
    
    # Fallback to file-based credentials
    creds_path = Path(__file__).parent.parent.parent / 'config' / 'credentials' / 'loyalty-service-account.json'
    if not creds_path.exists():
        raise FileNotFoundError("Service account credentials not found")
    
    return service_account.Credentials.from_service_account_file(
        str(creds_path),
        scopes=SCOPES
    )

async def get_stamp_loyalty(nomor_telepon: str) -> dict:
    """Get loyalty stamp information for a customer by phone number"""
    try:
        credentials = get_credentials()
        service = build('sheets', 'v4', credentials=credentials)

        sheet_id = os.getenv('LOYALTY_SHEET_ID')

        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=RANGE
        ).execute()
        
        values = result.get('values', [])
        
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
