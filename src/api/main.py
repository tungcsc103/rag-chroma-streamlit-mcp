from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv
from database.chroma_setup import ChromaDBManager
from utils.document_processor import DocumentProcessor
import uuid
from datetime import datetime

# Load environment variables
load_dotenv()

# API Configuration
API_PORT = int(os.getenv("API_PORT", "8001"))  # Default to port 8001 if not specified
API_HOST = os.getenv("API_HOST", "0.0.0.0")

app = FastAPI(
    title="Local RAG API",
    description="API for document storage and retrieval using ChromaDB",
    version="1.0.0"
)

# Initialize ChromaDB
db_manager = ChromaDBManager()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3

class QueryResponse(BaseModel):
    query: str
    documents: List[str]
    metadata: List[Dict]
    distances: List[float]

@app.get("/")
async def root():
    """
    Root endpoint that provides API information and supported file formats.
    """
    supported_formats = DocumentProcessor.get_supported_extensions()
    format_descriptions = {
        "pdf": "Adobe PDF documents",
        "doc": "Microsoft Word documents (legacy format)",
        "docx": "Microsoft Word documents",
        "txt": "Plain text files",
        "md": "Markdown documents",
        "csv": "Comma-separated values"
    }
    
    return {
        "message": "Welcome to Local RAG API",
        "status": "healthy",
        "supported_formats": supported_formats,
        "format_descriptions": {fmt: format_descriptions.get(fmt, "Supported document format") 
                              for fmt in supported_formats}
    }

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document to be processed and stored in the vector database.
    """
    try:
        # Validate file extension
        file_extension = file.filename.lower().split('.')[-1]
        if file_extension not in DocumentProcessor.get_supported_extensions():
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: {', '.join(DocumentProcessor.get_supported_extensions())}"
            )

        # Process the document
        doc_content = DocumentProcessor.process_document(file.file, file.filename)
        
        # Generate a unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Create metadata for the document
        metadata = {
            "filename": file.filename,
            "content_type": file.content_type,
            "upload_timestamp": str(datetime.now()),
            "file_type": file_extension,
            **doc_content.get("metadata", {})
        }
        
        # Add to ChromaDB
        db_manager.add_documents(
            texts=[doc_content["text"]],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        return {
            "message": f"Successfully uploaded {file.filename}",
            "document_id": doc_id,
            "metadata": metadata
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the RAG system with a question.
    """
    try:
        results = db_manager.query_documents(
            query_text=request.query,
            n_results=request.top_k
        )
        
        return {
            "query": request.query,
            "documents": results["documents"],
            "metadata": results["metadatas"],
            "distances": results["distances"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """
    Get statistics about the document collection.
    """
    try:
        stats = db_manager.get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    print(f"Starting FastAPI server on {API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT) 