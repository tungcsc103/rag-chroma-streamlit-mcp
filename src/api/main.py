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
from pathlib import Path
import tempfile
import logging

# Load environment variables
load_dotenv()

# API Configuration
API_PORT = int(os.getenv("API_PORT", "8001"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

app = FastAPI(
    title="Local RAG API",
    description="API for document storage and retrieval using ChromaDB",
    version="1.0.0"
)

# Initialize ChromaDB and Document Processor
db_manager = ChromaDBManager()
doc_processor = DocumentProcessor()

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
    group_by_document: Optional[bool] = True

class QueryResponse(BaseModel):
    query: str
    results: List[Dict]

@app.get("/")
async def root():
    """Root endpoint that provides API information and supported file formats."""
    supported_formats = DocumentProcessor.get_supported_extensions()
    format_descriptions = {
        "pdf": "Adobe PDF documents",
        "doc": "Microsoft Word documents (legacy format)",
        "docx": "Microsoft Word documents",
        "txt": "Plain text files",
        "md": "Markdown documents",
        "csv": "Comma-separated values",
        "epub": "Electronic publication format (eBooks)"
    }
    
    return {
        "message": "Welcome to Local RAG API",
        "status": "healthy",
        "supported_formats": supported_formats,
        "format_descriptions": {fmt: format_descriptions.get(fmt, "Supported document format") 
                              for fmt in supported_formats}
    }

@app.post("/upload")
async def upload_document(file: UploadFile):
    """
    Upload and process a document.
    Supports PDF, DOCX, DOC, TXT, and EPUB files.
    """
    try:
        # Validate file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in doc_processor.supported_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: {', '.join(doc_processor.supported_extensions)}"
            )

        # Create a temporary file to store the uploaded content
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            # Process the document
            try:
                result = doc_processor.process_document(temp_file.name, file.filename)
                
                # Add chunks to ChromaDB
                if result.get('chunks'):
                    document_id = db_manager.add_document_chunks(
                        chunks=result['chunks'],
                        document_id=None,  # Let ChromaDB generate an ID
                        base_metadata=result.get('metadata', {})
                    )
                    return {
                        "message": "Document processed successfully",
                        "document_id": document_id,
                        "status": "success"
                    }
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="No content could be extracted from the document"
                    )
                    
            finally:
                # Clean up the temporary file
                os.unlink(temp_file.name)
                
    except Exception as e:
        logging.error(f"Error processing upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query the RAG system with semantic search."""
    try:
        results = db_manager.query_documents(
            query_text=request.query,
            n_results=request.top_k,
            group_by_document=request.group_by_document
        )
        
        if request.group_by_document:
            return {
                "query": request.query,
                "results": results["results"]
            }
        else:
            # Format non-grouped results
            return {
                "query": request.query,
                "results": [{
                    "text": doc,
                    "metadata": meta,
                    "distance": dist
                } for doc, meta, dist in zip(
                    results["documents"],
                    results["metadatas"],
                    results["distances"]
                )]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its chunks."""
    try:
        db_manager.delete_document(document_id)
        return {"message": f"Successfully deleted document {document_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get statistics about the document collection."""
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