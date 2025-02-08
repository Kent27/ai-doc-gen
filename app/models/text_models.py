
from pydantic import BaseModel

class TextToDocRequest(BaseModel):
    text: str

class TextToDocResponse(BaseModel):
    download_url: str