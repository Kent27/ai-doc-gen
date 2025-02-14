from fastapi import FastAPI, HTTPException, File, UploadFile, Body, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
from app.services.document_service import generate_document
from pathlib import Path
import base64
from io import BytesIO
import os
from dotenv import load_dotenv
import docx
from .routers import assistant_router

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI
app = FastAPI()
app.include_router(assistant_router.router)

# Directory setup
TEMPLATES_DIR = Path("app/static/templates")
GENERATED_DOCS_DIR = Path("app/static/generated_docs")
GENERATED_DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Get host and port from environment variables
HOST_URL = os.getenv("HOST_URL", "http://localhost")
PORT = os.getenv("PORT", "8000")

# Check if running in production (assume no port needed)
IS_PRODUCTION = HOST_URL.startswith("https://") or os.getenv("PRODUCTION", "false").lower() == "true"

# Construct full host URL (include PORT only if not in production)
FULL_HOST_URL = f"{HOST_URL}:{PORT}" if not IS_PRODUCTION and PORT else HOST_URL


class DocumentRequest(BaseModel):
    """
    Pydantic model to validate the input request body.
    """
    json_data: dict  # JSON data as a dictionary
    template_base64: str = None  # Optional Base64-encoded DOCX file


def load_default_template() -> str:
    """
    Reads 'template1.docx' from the templates directory and returns its base64 encoding.

    Returns:
        str: Base64 encoded string of the default DOCX template.

    Raises:
        HTTPException: If the default template file is missing.
    """
    default_template_path = TEMPLATES_DIR / "template1.docx"

    if not default_template_path.exists():
        raise HTTPException(status_code=500, detail="Default template file 'template1.docx' not found")

    with open(default_template_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


@app.post("/generate-doc")
async def generate_doc(request: DocumentRequest):
    """
    Endpoint to generate a Word document based on JSON data and a base64 template.

    - If `template_base64` is not provided, it uses 'template1.docx' from the default location.
    - Returns a **download URL** instead of the actual file content.

    Args:
        request (DocumentRequest): JSON request body with document data and optional base64 template.

    Returns:
        JSONResponse: JSON object containing the download URL of the generated DOCX file.
    """
    try:
        # Use provided template or load the default one
        template_base64 = request.template_base64 or load_default_template()

        # Decode the base64 template into a BytesIO object
        template_bytes = base64.b64decode(template_base64)
        template_file = BytesIO(template_bytes)

        # Define output file path
        output_filename = "generated_document.docx"
        output_path = GENERATED_DOCS_DIR / output_filename

        # Generate the document
        await generate_document(json_data=request.json_data, template_file=template_file, output_file=output_path)

        # Construct the download URL with HOST and PORT
        download_url = f"{FULL_HOST_URL}/download/{output_filename}"

        return JSONResponse(content={"download_url": download_url})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Endpoint to serve generated documents for download.

    Args:
        filename (str): Name of the generated DOCX file.

    Returns:
        FileResponse: The requested DOCX file.
    """
    file_path = GENERATED_DOCS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=filename)


from app.models.api_models import APIConfig, APIResponse
from app.services.api_service import make_api_request

@app.post("/analyze-api", response_model=APIResponse)
async def analyze_api(config: APIConfig):
    """
    Endpoint to analyze an API by making a request and returning the response with its structure
    """
    return await make_api_request(config)


from app.models.text_models import TextToDocResponse
from app.services.ai_service import convert_text_to_json
import openai

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

async def extract_text_from_docx(file: UploadFile) -> str:
    """Extract text content from a Word document"""
    # Read the uploaded file into memory
    content = await file.read()
    doc_io = BytesIO(content)
    
    # Open the document using python-docx
    doc = docx.Document(doc_io)
    
    # Extract text from each paragraph
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    
    return '\n'.join(full_text)

@app.post("/text-to-doc", response_model=TextToDocResponse)
async def text_to_doc(
    request: Request,
    file: Optional[UploadFile] = File(None)
):
    """
    Convert text or Word document content to JSON using OpenAI, then generate a document.
    Accepts either a file upload through form-data or raw text in request body.
    """
    try:
        # Get input text either from file or raw body
        if file:
            if not file.filename.endswith('.docx'):
                raise HTTPException(status_code=400, detail="Only .docx files are supported")
            document_text = await extract_text_from_docx(file)
        else:
            # Read raw text from request body
            document_text = (await request.body()).decode()
            if not document_text:
                raise HTTPException(status_code=400, detail="Either file or text must be provided")

        # Rest of the processing remains the same
        convertedText = convert_text_to_json(document_text)
        template_base64 = load_default_template()
        template_bytes = base64.b64decode(template_base64)
        template_file = BytesIO(template_bytes)

        output_filename = "generated_document.docx"
        output_path = GENERATED_DOCS_DIR / output_filename

        await generate_document(json_data=convertedText['json_data'], template_file=template_file, output_file=output_path)

        download_url = f"{FULL_HOST_URL}/download/{output_filename}"
        return TextToDocResponse(download_url=download_url)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))