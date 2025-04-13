import chromadb
from chromadb.config import Settings
import os
import shutil
import stat
from typing import List, Dict, Optional, Union
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ChromaDBManager:
    def __init__(self, persist_directory: str = None, reset: bool = False):
        """
        Initialize ChromaDB with persistence
        
        Args:
            persist_directory (str): Directory where ChromaDB will store its data
            reset (bool): Whether to reset the database
        """
        # Get ChromaDB connection settings from environment
        chroma_host = os.getenv("CHROMA_HOST", "localhost")
        chroma_port = os.getenv("CHROMA_PORT", "8000")
        embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")

        print(f"Connecting to ChromaDB at {chroma_host}:{chroma_port}")
        print(f"Using embedding model: {embedding_model}")
        
        if persist_directory is None:
            # Get the absolute path to the project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            persist_directory = os.path.join(project_root, "data", "chroma")
        
        self.persist_directory = persist_directory
        print(f"ChromaDB persistence directory: {persist_directory}")
        
        # Reset the database if requested
        if reset and os.path.exists(persist_directory):
            print(f"Resetting ChromaDB at {persist_directory}")
            self._remove_readonly(persist_directory)
            shutil.rmtree(persist_directory)
        
        # Ensure the persist directory exists with proper permissions
        self._ensure_directory_permissions()
        
        try:
            # Initialize ChromaDB client with HTTP connection
            settings = Settings(
                chroma_api_impl="rest",
                chroma_server_host=chroma_host,
                chroma_server_http_port=chroma_port,
                anonymized_telemetry=False
            )

            self.client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port,
                settings=settings
            )
            
            # Use sentence-transformers for embeddings
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=embedding_model
            )
            
            try:
                # Try to get existing collection
                self.collection = self.client.get_collection(
                    name="documents",
                    embedding_function=self.embedding_function
                )
                print("Using existing collection 'documents'")
            except Exception as e:
                print(f"No existing collection found: {str(e)}")
                # Create new collection if it doesn't exist
                self.collection = self.client.create_collection(
                    name="documents",
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
                print("Created new collection 'documents'")
                
        except Exception as e:
            print(f"Error initializing ChromaDB: {str(e)}")
            # If there's an error, try to fix permissions and reinitialize
            self._fix_permissions()
            raise

    def _ensure_directory_permissions(self):
        """Ensure the persistence directory exists with proper permissions."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Set directory permissions to allow read/write
            os.chmod(self.persist_directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            
            # Set permissions for all existing files
            for root, dirs, files in os.walk(self.persist_directory):
                for d in dirs:
                    os.chmod(os.path.join(root, d), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                for f in files:
                    os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
        except Exception as e:
            print(f"Error setting permissions: {str(e)}")
            raise

    def _remove_readonly(self, path):
        """Remove readonly attributes from files and directories."""
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for d in dirs:
                    os.chmod(os.path.join(root, d), stat.S_IRWXU)
                for f in files:
                    os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR)
        else:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    def _fix_permissions(self):
        """Fix permissions for the ChromaDB directory and files."""
        try:
            print("Attempting to fix database permissions...")
            db_file = os.path.join(self.persist_directory, "chroma.sqlite3")
            if os.path.exists(db_file):
                os.chmod(db_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
            self._ensure_directory_permissions()
        except Exception as e:
            print(f"Error fixing permissions: {str(e)}")
            raise

    def add_document_chunks(
        self,
        chunks: List[Dict],
        document_id: str,
        base_metadata: Optional[Dict] = None
    ) -> None:
        """
        Add document chunks to the collection.
        
        Args:
            chunks: List of document chunks with their metadata
            document_id: Unique identifier for the document
            base_metadata: Base metadata for the document
        """
        if not chunks:
            raise ValueError("No chunks provided")
            
        if base_metadata is None:
            base_metadata = {}
            
        try:
            texts = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                chunk_text = chunk["text"]
                chunk_metadata = chunk["metadata"]
                
                # Combine base metadata with chunk metadata
                combined_metadata = {
                    **base_metadata,
                    **chunk_metadata,
                    "document_id": document_id  # Link chunk to parent document
                }
                
                # Generate chunk ID using the chunk_index from metadata
                chunk_id = f"{document_id}_chunk_{chunk_metadata.get('chunk_index', i)}"
                
                texts.append(chunk_text)
                metadatas.append(combined_metadata)
                ids.append(chunk_id)
            
            print(f"Adding {len(texts)} chunks for document {document_id}...")
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            print(f"Successfully added {len(texts)} chunks")
            
        except Exception as e:
            print(f"Error adding document chunks: {str(e)}")
            if "readonly database" in str(e).lower():
                self._fix_permissions()
                print("Retrying chunk addition after fixing permissions...")
                self.collection.add(
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
            else:
                raise

    def query_documents(
        self,
        query_text: str,
        n_results: int = 3,
        where: Optional[Dict] = None,
        group_by_document: bool = True
    ) -> Dict:
        """
        Query the collection to find similar chunks and optionally group by document.
        
        Args:
            query_text: The query text
            n_results: Number of results to return
            where: Filter conditions
            group_by_document: Whether to group results by parent document
            
        Returns:
            Dict: Query results containing chunks and their metadata
        """
        # Increase n_results when grouping to ensure we get enough unique documents
        search_n_results = n_results * 3 if group_by_document else n_results
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=search_n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        if not group_by_document:
            return {
                "ids": results["ids"][0],
                "documents": results["documents"][0],
                "metadatas": results["metadatas"][0],
                "distances": results["distances"][0]
            }
            
        # Group results by document_id
        grouped_results = {}
        for i, (chunk_id, text, metadata, distance) in enumerate(zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            doc_id = metadata.get("document_id") if metadata else None
            if doc_id not in grouped_results:
                grouped_results[doc_id] = {
                    "chunks": [],
                    "metadata": {k: v for k, v in metadata.items() if not k.startswith("chunk_")},
                    "best_distance": distance
                }
            grouped_results[doc_id]["chunks"].append({
                "text": text,
                "chunk_metadata": {k.replace("chunk_", ""): v for k, v in metadata.items() if k.startswith("chunk_")},
                "distance": distance
            })
            
        # Sort documents by best matching chunk
        sorted_docs = sorted(
            grouped_results.items(),
            key=lambda x: x[1]["best_distance"]
        )[:n_results]
        
        return {
            "results": [
                {
                    "document_id": doc_id,
                    "metadata": doc_data["metadata"],
                    "chunks": sorted(
                        doc_data["chunks"],
                        key=lambda x: x["distance"]
                    ),
                    "best_distance": doc_data["best_distance"]
                }
                for doc_id, doc_data in sorted_docs
            ]
        }

    def delete_document(self, document_id: str) -> None:
        """Delete all chunks belonging to a document."""
        try:
            # Find all chunks for this document
            results = self.collection.get(
                where={"document_id": document_id}
            )
            if results["ids"]:
                self.collection.delete(
                    ids=results["ids"]
                )
        except Exception as e:
            if "readonly database" in str(e).lower():
                self._fix_permissions()
                self.collection.delete(
                    where={"document_id": document_id}
                )
            else:
                raise

    def get_collection_stats(self) -> Dict:
        """
        Get statistics about the collection
        
        Returns:
            Dict: Collection statistics
        """
        try:
            # Get total number of chunks
            total_chunks = self.collection.count()
            
            # Get unique document count
            results = self.collection.get(
                include=["metadatas"]
            )
            unique_docs = len(set(
                meta.get("document_id")
                for meta in results["metadatas"]
                if meta and "document_id" in meta
            )) if results["metadatas"] else 0
            
            return {
                "total_chunks": total_chunks,
                "unique_documents": unique_docs,
                "name": self.collection.name,
                "metadata": self.collection.metadata
            }
        except Exception as e:
            print(f"Error getting collection stats: {str(e)}")
            raise

# Example usage
if __name__ == "__main__":
    # Initialize the ChromaDB manager
    db_manager = ChromaDBManager()
    
    # Example documents
    sample_texts = [
        "This is a sample document about AI.",
        "ChromaDB is a vector database.",
        "RAG systems combine retrieval with generation."
    ]
    
    # Add documents
    db_manager.add_document_chunks(sample_texts, "doc_1")
    
    # Query example
    results = db_manager.query_documents("Tell me about AI")
    print("Query results:", results) 