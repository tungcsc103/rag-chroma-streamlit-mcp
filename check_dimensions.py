import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

def check_collection_dimensions():
    # Initialize the client with BGE embedding function
    client = chromadb.HttpClient(
        host="localhost",
        port=8000,
        settings=Settings()
    )
    
    # Initialize BGE embedding function
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="BAAI/bge-base-en-v1.5"
    )
    
    # Get the collection
    collection = client.get_collection(
        name="documents",
        embedding_function=embedding_function
    )
    
    # Get collection info
    print("\nCollection Information:")
    print(f"Name: {collection.name}")
    print(f"Metadata: {collection.metadata}")
    
    # Add a small piece of text to check dimensions
    try:
        collection.add(
            documents=["test document"],
            metadatas=[{"test": "test"}],
            ids=["test_id"]
        )
        print("\nSuccessfully added test document")
    except Exception as e:
        print(f"\nError adding document (this can show dimension mismatch): {str(e)}")
    
    # Get the first item to check its embedding
    try:
        results = collection.get(
            ids=["test_id"],
            include=["embeddings"]
        )
        if results and "embeddings" in results and len(results["embeddings"]) > 0:
            embeddings = results["embeddings"][0]
            if isinstance(embeddings, (list, tuple)):
                print(f"\nEmbedding dimensions: {len(embeddings)}")
            else:
                print(f"\nEmbedding type: {type(embeddings)}")
                print(f"\nEmbedding shape: {embeddings.shape if hasattr(embeddings, 'shape') else 'unknown'}")
    except Exception as e:
        print(f"\nError getting embeddings: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Clean up test document
    try:
        collection.delete(ids=["test_id"])
    except:
        pass

if __name__ == "__main__":
    check_collection_dimensions() 