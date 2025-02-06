# ai-doc-gen
Generate a docx report based on the provided template

## Setup

### Prerequisites
- Docker and Docker Compose
- Or: Python 3.9+ with Conda/Miniconda installed

### Environment Configuration
1. Clone the repository
2. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
The default environment variables are:
- PORT=8085
- HOST_URL=http://localhost
- PRODUCTION=false

### Installation & Running

#### Using Docker (Recommended)
1. Build and run the container:
```bash
docker-compose up --build
```
The application will be available at `http://localhost:8085`

#### Manual Setup with Conda
1. Create and activate the Conda environment:
```bash
conda env create -f environment.yml
conda activate docgen
```
2. Start the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8085 --reload
```

## Usage
1. Prepare your document template in docx format
2. Make API calls to the endpoint with your template and data
3. Retrieve the generated document

## API Documentation
The following endpoints are available:

### Document Generation
#### `POST /generate-doc`
Generate a document from JSON data and an optional template.

**Request Body:**
```json
{
    "json_data": object,         // Required: Data to populate the template
    "template_base64": string    // Optional: Base64 encoded DOCX template
}
```

**Response:**
```json
{
    "download_url": string       // URL to download the generated document
}
```

### Document Download
#### `GET /download/{filename}`
Download a generated document.

**Response:**
- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Body: Generated DOCX file

### API Analysis
#### `POST /analyze-api`
Analyze an API by making a request and returning its structure.

**Request Body:**
```json
{
    "url": string,              // API endpoint URL
    "method": string,           // HTTP method
    "headers": object,          // Optional: Request headers
    "params": object,           // Optional: Query parameters
    "body": object,             // Optional: Request body
    "timeout": number          // Optional: Request timeout in seconds
}
```

**Response:**
```json
{
    "status_code": number,
    "success": boolean,
    "data": any,
    "structure": object,
    "error": string            // Optional: Error message if request fails
}
```
