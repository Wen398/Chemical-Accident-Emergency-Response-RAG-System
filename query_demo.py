import chromadb
import sys

# Configuration
DB_DIR = "erg_chroma_db"

def main():
    if len(sys.argv) < 2:
        print("Usage: python query_demo.py <search_query>")
        print("Example: python query_demo.py 'Chlorine'")
        return

    query_text = sys.argv[1]
    
    print(f"Connecting to DB at {DB_DIR}...")
    client = chromadb.PersistentClient(path=DB_DIR)
    
    # 1. First, search for the material to identify what we are dealing with
    print(f"\n--- Step 1: Searching for Material '{query_text}' ---")
    materials_col = client.get_collection("erg_materials")
    
    # Query logic: We look for the top match
    material_results = materials_col.query(
        query_texts=[query_text],
        n_results=1
    )
    
    if not material_results['ids'][0]:
        print("No material found.")
        return

    # Extract info from the best match
    best_material_id = material_results['ids'][0][0]
    best_material_meta = material_results['metadatas'][0][0]
    best_material_doc = material_results['documents'][0][0]
    
    print(f"Found Material: {best_material_meta['name']} (UN: {best_material_meta['un_id']})")
    print(f"Guide Number: {best_material_meta['guide_no']}")
    print(f"Is TIH? {best_material_meta['is_tih']}")
    print(f"Is Water Reactive? {best_material_meta['is_water_reactive']}")
    
    if best_material_meta['is_tih']:
        print(f"Small Spill Isolation: {best_material_meta['small_spill_isolation']}")
        print(f"Large Spill Isolation: {best_material_meta['large_spill_isolation']}")
        
    # 2. Now use the Guide Number to find specific response info
    guide_no = best_material_meta['guide_no']
    print(f"\n--- Step 2: Retrieving Guide {guide_no} Info ---")
    
    guides_col = client.get_collection("erg_guides")
    
    # We want to retrieve all sections for this guide.
    # We can use a 'where' filter on metadata instead of semantic search if we just want to read the guide.
    # Or we can semantic search specific questions against this guide.
    
    # Let's show semantic search scoped to this guide: "What to do for fire?"
    fire_query = "fire fighting measures"
    print(f"Querying Guide {guide_no} for: '{fire_query}'")
    
    guide_results = guides_col.query(
        query_texts=[fire_query],
        n_results=1,
        where={"guide_no": guide_no} # Crucial: Context Filtering
    )
    
    if guide_results['ids'][0]:
        print("\nRelevant Guide Section:")
        print(guide_results['documents'][0][0][:500] + "...") # Print first 500 chars
    else:
        print("No specific guide section found.")

if __name__ == "__main__":
    main()
