import chromadb
from chromadb.utils import embedding_functions
import os

# Configuration
DB_DIR = "erg_chroma_db_cn"

def test_rag_db():
    print(f"Connecting to ChromaDB at '{DB_DIR}'...")
    
    if not os.path.exists(DB_DIR):
        print(f"Error: Database directory '{DB_DIR}' not found. Did you run build_rag_db_cn.py?")
        return

    # Initialize Embedding Function (Must match the one used during build)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    
    client = chromadb.PersistentClient(path=DB_DIR)
    
    try:
        collection = client.get_collection(name="erg_cn", embedding_function=ef)
        print(f"Successfully loaded collection '{collection.name}' with {collection.count()} documents.")
    except Exception as e:
        print(f"Error loading collection: {e}")
        return

    # Test Scenarios
    scenarios = [
        {
            "name": "Lookup by Chemical Name (Chinese)",
            "query": "氯氣",
            "n_results": 3,
            "filter": {"type": "material"}
        },
        {
            "name": "Lookup by UN ID",
            "query": "UN 1017",
            "n_results": 1,
            "filter": {"type": "material"} 
            # Note: Chroma semantic search for exact numbers can be tricky, but "UN 1017" usually works.
            # Ideally we would use metadata filter for UN ID, but let's test semantic first.
        },
        {
            "name": "Lookup Guide Content (Safety)",
            "query": "發生火災時如何處理 Guide 124?",
            "n_results": 1,
            "filter": {"type": "guide"} 
        },
        {
            "name": "Mixed Query (Isolation Distance)",
            "query": "Ammonia 的隔離距離是多少?",
            "n_results": 3,
            # We want materials to see the enriched green table data
            "filter": {"type": "material"}
        }
    ]

    print("\n--- Starting RAG Tests ---")

    for scenario in scenarios:
        print(f"\n[Test Case] {scenario['name']}")
        print(f"Query: \"{scenario['query']}\"")
        
        results = collection.query(
            query_texts=[scenario['query']],
            n_results=scenario['n_results'],
            where=scenario.get("filter")
        )
        
        if not results['documents'][0]:
            print("  No results found.")
            continue

        for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
            print(f"  Result {i+1} (Distance: {dist:.4f}):")
            
            # Print Metadata clearly
            if meta['type'] == 'material':
                print(f"    - Type: Material")
                print(f"    - Name: {meta.get('name')}")
                print(f"    - UN ID: {meta.get('un_id')}")
                print(f"    - Guide No: {meta.get('guide_no')}")
                
                # Check for Green Table info in doc text
                if "Table 1" in doc or "隔離" in doc:
                    print(f"    - Has Isolation Data: Yes")
                else:
                    print(f"    - Has Isolation Data: No")
                    
            elif meta['type'] == 'guide':
                print(f"    - Type: Guide")
                print(f"    - Guide No: {meta.get('guide_no')}")
                # Print snippet of content
                snippet = doc.replace("\n", " ")[:150] + "..."
                print(f"    - Content Snippet: {snippet}")

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    test_rag_db()
