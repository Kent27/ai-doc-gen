from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse
from app.services import generate_document
from pathlib import Path
import uvicorn

app = FastAPI()

# Directory to save generated documents
GENERATED_DOCS_DIR = Path("app/static/generated_docs")
GENERATED_DOCS_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/generate-doc")
async def generate_doc(
    json_data: str = Form(...),
    template_file: UploadFile = None,
):
    """
    Endpoint to generate a Word document based on JSON data and a template.

    Args:
        json_data (str): JSON data as a string.
        template_file (UploadFile): DOCX template file.

    Returns:
        FileResponse: The generated DOCX file.
    """
    output_file = GENERATED_DOCS_DIR / f"generated_{template_file.filename}"
    await generate_document(json_data, template_file.file, output_file)
    return FileResponse(output_file, filename=output_file.name)