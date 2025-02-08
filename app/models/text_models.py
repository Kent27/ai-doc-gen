from pydantic import BaseModel

class TextToDocResponse(BaseModel):
    download_url: str