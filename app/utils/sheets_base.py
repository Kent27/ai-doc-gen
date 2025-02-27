import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pathlib import Path
from typing import Optional, List

class GoogleSheetsBase:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self, sheet_id: str, range_name: str):
        self.sheet_id = sheet_id
        self.range_name = range_name
        self._service = None
    
    @property
    def service(self):
        """Lazy load the Google Sheets service"""
        if not self._service:
            credentials = self._get_credentials()
            self._service = build('sheets', 'v4', credentials=credentials)
        return self._service
    
    def _get_credentials(self):
        """Get credentials from file"""
        creds_path = Path(__file__).parent.parent.parent / 'config' / 'credentials' / 'loyalty-service-account.json'
        if not creds_path.exists():
            raise FileNotFoundError("Service account credentials not found")
        
        return service_account.Credentials.from_service_account_file(
            str(creds_path),
            scopes=self.SCOPES
        )
    
    async def get_values(self) -> List[List[str]]:
        """Get all values from the specified range"""
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.sheet_id,
            range=self.range_name
        ).execute()
        
        return result.get('values', [])
    
    async def update_values(self, range_name: str, values: List[List[str]], value_input_option: str = 'RAW'):
        """Update values in the specified range"""
        body = {'values': values}
        self.service.spreadsheets().values().update(
            spreadsheetId=self.sheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body
        ).execute()
    
    async def append_values(self, values: List[List[str]], range_name: Optional[str] = None, value_input_option: str = 'RAW'):
        """Append values to the sheet"""
        body = {'values': values}
        self.service.spreadsheets().values().append(
            spreadsheetId=self.sheet_id,
            range=range_name if range_name else self.range_name,
            valueInputOption=value_input_option,
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
