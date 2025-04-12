import chromadb
from chromadb.config import Settings
import os
import shutil
import stat
from typing import List, Dict, Optional
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
        embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

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

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Add documents to the collection
        
        Args:
            texts (List[str]): List of document texts to add
            metadatas (List[Dict], optional): Metadata for each document
            ids (List[str], optional): Custom IDs for each document
        """
        if not ids:
            # Generate simple IDs if none provided
            ids = [f"doc_{i}" for i in range(len(texts))]
            
        if not metadatas:
            metadatas = [{} for _ in texts]
        
        try:
            print(f"Adding {len(texts)} documents to ChromaDB...")
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            print(f"Successfully added {len(texts)} documents to ChromaDB")
        except Exception as e:
            print(f"Error adding documents to ChromaDB: {str(e)}")
            # Try to fix permissions if we get a readonly error
            if "readonly database" in str(e).lower():
                self._fix_permissions()
                # Retry the operation
                print("Retrying document addition after fixing permissions...")
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
        where: Optional[Dict] = None
    ) -> Dict:
        """
        Query the collection to find similar documents
        
        Args:
            query_text (str): The query text
            n_results (int): Number of results to return
            where (Dict, optional): Filter conditions
            
        Returns:
            Dict: Query results containing documents and their metadata
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        
        return {
            "ids": results["ids"][0],
            "documents": results["documents"][0],
            "metadatas": results["metadatas"][0],
            "distances": results["distances"][0]
        }

    def delete_document(self, document_id: str) -> None:
        """
        Delete a document from the collection
        
        Args:
            document_id (str): ID of the document to delete
        """
        try:
            self.collection.delete(ids=[document_id])
        except Exception as e:
            if "readonly database" in str(e).lower():
                self._fix_permissions()
                # Retry the operation
                self.collection.delete(ids=[document_id])
            else:
                raise

    def get_collection_stats(self) -> Dict:
        """
        Get statistics about the collection
        
        Returns:
            Dict: Collection statistics
        """
        return {
            "count": self.collection.count(),
            "name": self.collection.name,
            "metadata": self.collection.metadata
        }

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
    db_manager.add_documents(sample_texts)
    
    # Query example
    results = db_manager.query_documents("Tell me about AI")
    print("Query results:", results) 