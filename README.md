# Local RAG System

This project implements a local Retrieval-Augmented Generation (RAG) system using LangChain and ChromaDB.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your configuration:
```env
OPENAI_API_KEY=your_api_key_here
```

## Project Structure

- `src/`: Main source code directory
  - `embeddings/`: Embedding models and utilities
  - `database/`: ChromaDB setup and operations
  - `api/`: FastAPI endpoints
- `data/`: Directory for storing document collections
- `tests/`: Test files

## Usage

1. Start the API server:
```bash
uvicorn src.api.main:app --reload
```

2. The API will be available at `http://localhost:8000`

## Features

- Local document storage using ChromaDB
- Document embedding using Sentence Transformers
- REST API for document ingestion and querying
- Retrieval-augmented generation capabilities

## License

MIT 