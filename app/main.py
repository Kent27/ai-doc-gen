from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services import generate_document
from pathlib import Path
import base64
from io import BytesIO

app = FastAPI()

# Directory setup
TEMPLATES_DIR = Path("app/static/templates")
GENERATED_DOCS_DIR = Path("app/static/generated_docs")
GENERATED_DOCS_DIR.mkdir(parents=True, exist_ok=True)


class DocumentRequest(BaseModel):
    json_data: dict  # JSON data as a dictionary
    template_base64: str = None  # Optional Base64-encoded DOCX file


def load_default_template():
    """
    Reads 'template1.docx' from the templates directory and returns its base64 encoding.
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

    If template_base64 is not provided, it uses 'template1.docx' from the default location.

    Args:
        request (DocumentRequest): JSON request body with document data and optional base64 template.

    Returns:
        FileResponse: The generated DOCX file.
    """
    try:
        # Use provided template or default one
        template_base64 = request.template_base64 or load_default_template()

        # Decode the base64 template into a BytesIO object
        template_bytes = base64.b64decode(template_base64)
        template_file = BytesIO(template_bytes)

        output_file = GENERATED_DOCS_DIR / "generated_document.docx"
        await generate_document(json_data=request.json_data, template_file=template_file, output_file=output_file)

        return FileResponse(output_file, filename=output_file.name)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))