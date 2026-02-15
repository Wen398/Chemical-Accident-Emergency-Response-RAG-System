import chromadb
import sys
import os

# Configuration
DB_DIR = "erg_chroma_db"

def main():
    print(f"Connecting to ChromaDB at {os.path.abspath(DB_DIR)}...")
    try:
        client = chromadb.PersistentClient(path=DB_DIR)
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")
        return

    # Check collections
    try:
        materials_col = client.get_collection("erg_materials")
        guides_col = client.get_collection("erg_guides")
        print("Successfully connected to collections: 'erg_materials' and 'erg_guides'.")
    except Exception as e:
        print(f"Error accessing collections: {e}")
        return

    # Test Case: Ammonia (UN 1005) - Using metadata filtering to verify data integrity
    test_un_id = "1005"
    print(f"\n--- TEST: Retrieving specific record for UN {test_un_id} (Ammonia) ---")
    
    results = materials_col.query(
        query_texts=[""], # Empty query, rely on filter
        n_results=1,
        where={"un_id": test_un_id}
    )
    
    if not results['ids'][0]:
        print("TEST FAILED: No material found.")
        return

    # Inspect the result
    idx = 0
    doc_id = results['ids'][0][idx]
    meta = results['metadatas'][0][idx]
    document = results['documents'][0][idx]
    
    print(f"Match Found: {meta['name']} (UN: {meta.get('un_id', 'N/A')})")
    print(f"Guide No: {meta.get('guide_no', 'N/A')}")
    print(f"Is TIH: {meta.get('is_tih', False)}")
    
    # Check for Green Table 1 Data
    print("\n[Green Table 1 Data Check]")
    print(f"Small Spill Isolation: {meta.get('small_iso', 'N/A')}")
    print(f"Large Spill Isolation: {meta.get('large_iso', 'N/A')}")
    print(f"Large Spill Note: {meta.get('large_note', 'N/A')}") # Should be "Refer to Table 3"

    # Check for Table 3 Data in Document Content
    print("\n[Green Table 3 Data Check]")
    if "Detailed Large Spill Data (Table 3)" in document:
        print("SUCCESS: Table 3 data found in document content.")
        # Print a snippet
        start = document.find("Detailed Large Spill Data (Table 3)")
        print("Snippet:\n" + document[start:start+200] + "...")
    else:
        print("WARNING: Table 3 data NOT found in document content.")

    # Test Guide Retrieval
    guide_no = meta.get('guide_no')
    if guide_no:
        print(f"\n--- TEST: Retrieving Guide {guide_no} ---")
        
        # Test 1: Fetch Potential Hazards
        print("Querying for: POTENTIAL HAZARDS")
        guide_results = guides_col.query(
            query_texts=[f"GUIDE {guide_no} POTENTIAL HAZARDS"], 
            n_results=1,
            # ChromaDB filters require $and for multiple conditions, not just a flat dict
            where={
                "$and": [
                    {"guide_no": guide_no},
                    {"section": "POTENTIAL HAZARDS"}
                ]
            }
        )
        
        if guide_results['ids'][0]:
            g_meta = guide_results['metadatas'][0][0]
            g_doc = guide_results['documents'][0][0]
            print(f"Guide Section Found: {g_meta['section']}")
            print(f"Content Preview: {g_doc[:100]}...\n")
        else:
            print(f"WARNING: Guide {guide_no} POTENTIAL HAZARDS not found.\n")

        # Test 2: Fetch Public Safety without filter just to see semantic search behavior
        print("Querying for: PUBLIC SAFETY (Semantic Search Only)")
        guide_results_sem = guides_col.query(
            query_texts=[f"GUIDE {guide_no} PUBLIC SAFETY"], 
            n_results=1,
            where={"guide_no": guide_no}
        )
        
        if guide_results_sem['ids'][0]:
            g_meta = guide_results_sem['metadatas'][0][0]
            print(f"Guide Section Found: {g_meta['section']}")
        else: 
            print("Not found.")

    print("\n--- RAG System Test Complete ---")

if __name__ == "__main__":
    main()
