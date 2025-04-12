# Local RAG System

This project implements a local Retrieval-Augmented Generation (RAG) system using LangChain, ChromaDB, and Streamlit.

## Running with Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/tungcsc103/rag-mcp-chroma-streamlit.git
cd rag-mcp-chroma-streamlit
```

2. Create a `.env` file in the project root with your configuration:
```env
# Embedding Model Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # Default embedding model

# ChromaDB Configuration
CHROMA_SERVER_HOST=chroma-db
CHROMA_SERVER_PORT=8000

# Backend Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001

# Frontend Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

3. Build and start the services using Docker Compose:
```bash
docker compose up --build
```

The services will be available at:
- Frontend (Streamlit): http://localhost:8501
- Backend API: http://localhost:8001
- ChromaDB: http://localhost:8000

## Claude Desktop Integration

To use this RAG system with Claude Desktop, you'll need to configure the Chroma MCP client in your `claude_desktop_config.json` file. Here are the different configuration options:

### 1. Using Local Docker Setup (Recommended)

Add the following to your `claude_desktop_config.json`:
```json
"chroma": {
    "command": "uvx",
    "args": [
        "chroma-mcp",
        "--client-type",
        "http",
        "--host",
        "localhost",
        "--port",
        "8000"
    ]
}
```

This configuration will connect to your locally running ChromaDB instance through Docker.

### 2. Using Persistent Storage

For persistent data storage:
```json
"chroma": {
    "command": "uvx",
    "args": [
        "chroma-mcp",
        "--client-type",
        "persistent",
        "--data-dir",
        "/full/path/to/your/data/directory"
    ]
}
```

### 3. Using Chroma Cloud

To connect to Chroma Cloud:
```json
"chroma": {
    "command": "uvx",
    "args": [
        "chroma-mcp",
        "--client-type",
        "cloud",
        "--tenant",
        "your-tenant-id",
        "--database",
        "your-database-name",
        "--api-key",
        "your-api-key"
    ]
}
```

### Environment Variables for Claude Desktop

You can also use environment variables for configuration. Create a `.env` file:
```env
# Common variables
CHROMA_CLIENT_TYPE="http"  # or "cloud", "persistent"

# For persistent client
CHROMA_DATA_DIR="/full/path/to/your/data/directory"

# For cloud client (Chroma Cloud)
CHROMA_TENANT="your-tenant-id"
CHROMA_DATABASE="your-database-name"
CHROMA_API_KEY="your-api-key"

# For HTTP client (self-hosted)
CHROMA_HOST="localhost"
CHROMA_PORT="8000"
```

Then specify the path in your Claude Desktop config:
```json
"chroma": {
    "command": "uvx",
    "args": [
        "chroma-mcp",
        "--dotenv-path",
        "/path/to/your/.env"
    ]
}
```

## Local Development Setup

If you prefer to run the services locally without Docker:

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install system dependencies for document processing:
```bash
# For Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y libreoffice libreoffice-writer fonts-liberation fonts-dejavu fontconfig

# For macOS
brew install libreoffice
```

4. Start the services:

Start ChromaDB:
```bash
docker compose up chroma-db
```

Start the Backend:
```bash
cd src
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

Start the Frontend:
```bash
streamlit run src/frontend/app.py
```

## Project Structure

- `src/`: Main source code directory
  - `api/`: FastAPI backend service
  - `database/`: ChromaDB setup and operations
  - `embeddings/`: Embedding models and utilities
  - `frontend/`: Streamlit frontend application
  - `utils/`: Utility functions including document processing
- `data/`: Directory for storing document collections
- `tests/`: Test files
- `docker-compose.yml`: Docker Compose configuration
- `backend.Dockerfile`: Backend service Dockerfile
- `frontend.Dockerfile`: Frontend service Dockerfile

## Features

- Document Processing:
  - Supports multiple document formats: PDF, DOCX, DOC, TXT
  - Automatic text extraction and processing
  - Document chunking and embedding
- Vector Database:
  - Local document storage using ChromaDB
  - Document embedding using Sentence Transformers
  - Efficient similarity search
- User Interface:
  - Modern Streamlit frontend
  - Document upload and management
  - Interactive chat interface
- REST API:
  - Document ingestion and querying
  - Retrieval-augmented generation capabilities
  - Health check endpoints

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EMBEDDING_MODEL` | Sentence Transformer model to use | sentence-transformers/all-MiniLM-L6-v2 |
| `CHROMA_SERVER_HOST` | ChromaDB server host | chroma-db |
| `CHROMA_SERVER_PORT` | ChromaDB server port | 8000 |
| `BACKEND_HOST` | Backend service host | 0.0.0.0 |
| `BACKEND_PORT` | Backend service port | 8001 |
| `STREAMLIT_SERVER_PORT` | Streamlit server port | 8501 |
| `STREAMLIT_SERVER_ADDRESS` | Streamlit server address | 0.0.0.0 |

## Troubleshooting

1. If you encounter document processing issues:
   - Ensure LibreOffice is properly installed
   - Check file permissions in the upload directory
   - Verify the document format is supported

2. If ChromaDB connection fails:
   - Verify ChromaDB service is running
   - Check the ChromaDB host and port configuration
   - Ensure network connectivity between services

3. For Docker-related issues:
   - Ensure Docker and Docker Compose are up to date
   - Check container logs: `docker compose logs [service-name]`
   - Verify port mappings and network configuration

## License

MIT 