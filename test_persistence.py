from src.database.chroma_setup import ChromaDBManager
import time

def test_persistence():
    # Initialize the database with reset
    print("\n1. Initializing database with reset...")
    db = ChromaDBManager(reset=True)
    
    # Add a test document
    test_doc = "This is a test document to verify persistence."
    doc_metadata = {"test": "persistence_check", "timestamp": str(time.time())}
    
    print("\n2. Adding test document...")
    db.add_documents(
        texts=[test_doc],
        metadatas=[doc_metadata]
    )
    
    # Get initial count
    initial_stats = db.get_collection_stats()
    print(f"\n3. Initial collection stats:")
    print(f"   - Document count: {initial_stats['count']}")
    
    # Create a new instance to verify persistence
    print("\n4. Creating new database instance...")
    db2 = ChromaDBManager()
    
    # Get stats from new instance
    new_stats = db2.get_collection_stats()
    print(f"\n5. New instance collection stats:")
    print(f"   - Document count: {new_stats['count']}")
    
    # Query the document to verify content
    print("\n6. Querying test document...")
    results = db2.query_documents("test document")
    
    print("\n7. Query results:")
    print(f"   - Found documents: {len(results['documents'])}")
    if results['documents']:
        print(f"   - Document content: {results['documents'][0]}")
        print(f"   - Document metadata: {results['metadatas'][0]}")

if __name__ == "__main__":
    test_persistence() 