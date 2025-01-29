from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from app.services import generate_document
from pathlib import Path
import base64
from io import BytesIO
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Directory setup
TEMPLATES_DIR = Path("app/static/templates")
GENERATED_DOCS_DIR = Path("app/static/generated_docs")
GENERATED_DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Get host and port from environment variables
HOST_URL = os.getenv("HOST_URL", "http://localhost")
PORT = os.getenv("PORT", "8000")

# Construct the full host URL including port
FULL_HOST_URL = f"{HOST_URL}:{PORT}" if PORT else HOST_URL


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