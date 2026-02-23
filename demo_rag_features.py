import chromadb
import os
import sys
import json
from typing import List, Dict, Any

# Configuration
DB_DIR = "erg_chroma_db"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

class RAGDemo:
    def __init__(self):
        print(f"\n[INIT] Connecting to ChromaDB at {os.path.abspath(DB_DIR)}...")
        try:
            self.client = chromadb.PersistentClient(path=DB_DIR)
            self.materials_col = self.client.get_collection("erg_materials")
            self.guides_col = self.client.get_collection("erg_guides")
            print("[INIT] Connection successful. Collections loaded.\n")
        except Exception as e:
            print(f"[ERROR] Failed to connect to ChromaDB: {e}")
            sys.exit(1)

    def print_separator(self, title):
        print("\n" + "="*60)
        print(f" {title}")
        print("="*60)

    def search_semantic(self, query: str, collection_name: str = "materials", n_results: int = 3):
        """
        Demonstrates pure semantic search (vector similarity).
        Pass a natural language query.
        """
        collection = self.materials_col if collection_name == "materials" else self.guides_col
        print(f"\n[QUERY] Semantic Search: '{query}' ({collection_name})")
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        self._display_results(results)

    def search_metadata(self, filters: Dict[str, Any], n_results: int = 5):
        """
        Demonstrates metadata filtering (structured search).
        Pass a filter dictionary compatible with ChromaDB 'where'.
        """
        display_filters = json.dumps(filters, indent=2)
        print(f"\n[QUERY] Metadata Search with filters:\n{display_filters}")
        
        # Determine collection based on filter keys (simple heuristic)
        if "guide_no" in filters and "section" in filters and len(filters) == 2:
             collection = self.guides_col
        else:
             collection = self.materials_col

        # Use get() for pure metadata filtering
        # Note: get() returns flat lists, while query() returns lists of lists.
        # We wrap them to reuse _display_results logic which expects query() format.
        flat_results = collection.get(
            where=filters,
            limit=n_results
        )
        
        # mimic query() structure
        results = {
            'ids': [flat_results['ids']],
            'documents': [flat_results['documents']],
            'metadatas': [flat_results['metadatas']],
            'distances': None 
        }
        
        self._display_results(results)

    def search_hybrid(self, query: str, filters: Dict[str, Any], n_results: int = 3):
        """
        Demonstrates Hybrid Search: Semantic Vector Search + Metadata Filtering.
        """
        print(f"\n[QUERY] Hybrid Search: '{query}' + Filters: {json.dumps(filters)}")
        
        results = self.materials_col.query(
            query_texts=[query],
            n_results=n_results,
            where=filters
        )
        
        self._display_results(results)

    def retrieve_guide(self, guide_no: str):
        """
        Retrieves the guide content for a specific guide number.
        This simulates the second step of RAG: Get Context -> Get Actionable Guide.
        """
        print(f"\n[ACTION] Retrieving Guide #{guide_no}...")
        
        # We want all sections for the guide
        results = self.guides_col.query(
            query_texts=[f"Guide {guide_no} content"], # query helps sort by relevance if needed, but filter is key
            where={"guide_no": guide_no},
            n_results=5 # Usually 3 sections per guide: Hazards, Safety, Response
        )
        
        if not results['ids'][0]:
            print("  No guide found.")
            return

        # Display sections
        for i in range(len(results['ids'][0])):
            meta = results['metadatas'][0][i]
            # Print a snippet of the text
            text = results['documents'][0][i]
            snippet = text[:200].replace('\n', ' ') + "..."
            print(f"  - Section: {meta.get('section', 'Unknown')}")
            print(f"    Content: {snippet}")

    def _display_results(self, results):
        if not results['ids'][0]:
            print("  [No results found]")
            return
            
        for i in range(len(results['ids'][0])):
            doc_id = results['ids'][0][i]
            meta = results['metadatas'][0][i]
            # distance = results['distances'][0][i] if 'distances' in results and results['distances'] else "N/A"
            # ChromaDB query returns distances by default
            
            print(f"  Result #{i+1}:")
            # print(f"    ID: {doc_id}")
            # print(f"    Distance: {distance}")
            
            # Display relevant metadata based on what keys exist
            display_keys = ['name', 'un_id', 'guide_no', 'is_tih', 'section']
            info = []
            for k in display_keys:
                if k in meta:
                    info.append(f"{k}: {meta[k]}")
            print(f"    Metadata: {{ {', '.join(info)} }}")
            
            # Text Snippet
            text = results['documents'][0][i]
            snippet = text.strip()[:150].replace('\n', ' ') + "..."
            print(f"    Excerpt: {snippet}")
            print()

def main():
    demo = RAGDemo()
    
    # --- Scenario 1: Natural Language / Colloquial Search ---
    demo.print_separator("SCENARIO 1: Natural Language / Colloquial Search")
    print("User asks: 'something focused on smelling like rotten eggs' (implying Hydrogen Sulfide)")
    demo.search_semantic("gas smelling like rotten eggs")
    
    print("User asks: 'extremely flammable liquid'")
    demo.search_semantic("extremely flammable liquid")

    # --- Scenario 2: Metadata Filtering (Structured Query) ---
    demo.print_separator("SCENARIO 2: Metadata Filtering (Precision Search)")
    print("Task: Find materials with UN ID 1017 (Chlorine)")
    demo.search_metadata({"un_id": "1017"})
    
    print("Task: Find materials that are Toxic Inhalation Hazards (is_tih = True)")
    # Note: ChromaDB requires boolean to be passed correctly if stored as boolean
    # Based on build_rag_db.py, 'is_tih' is stored as boolean.
    demo.search_metadata({"is_tih": True}, n_results=3)

    # --- Scenario 3: Hybrid Search (Semantic + Filters) ---
    demo.print_separator("SCENARIO 3: Hybrid Search (Context + Constraints)")
    print("User asks: 'gases that react with water' BUT restricted to only TIH materials")
    demo.search_hybrid(
        query="reacts with water violently", 
        filters={"is_tih": True},
        n_results=3
    )

    # --- Scenario 4: The Full RAG Workflow ---
    demo.print_separator("SCENARIO 4: Full RAG Workflow Simulation")
    # Step 1: User Query -> Find Material
    user_query = "What do I do for a Chlorine spill?"
    print(f"User Query: '{user_query}'")
    
    # 1. Search for material
    print(">>> Step 1: Retrieving Material Info...")
    # Ideally search specifically for 'Chlorine'
    # Increasing n_results to 3 to see if "Chlorine (UN 1017)" appears in the top results
    results = demo.materials_col.query(query_texts=["Chlorine spill"], n_results=3)
    
    # Check if we found any results
    if results['ids'][0]:
        found_target = False
        target_guide_no = None
        
        print(f"    [Trace] Top 3 results for 'Chlorine spill':")
        for i in range(len(results['ids'][0])):
            meta = results['metadatas'][0][i]
            print(f"      #{i+1}: {meta['name']} (UN: {meta.get('un_id')})")
            
            # Simple heuristic: prioritize exact match or simple name
            if meta['name'].lower() == "chlorine":
                target_guide_no = meta['guide_no']
                found_target = True
                print(f"      -> MATCH FOUND! Selected: {meta['name']}")

        # Fallback to first result if no exact match found (simplified logic)
        if not found_target:
             first_match = results['metadatas'][0][0]
             target_guide_no = first_match['guide_no']
             print(f"      -> No exact 'Chlorine' match. Defaulting to top result: {first_match['name']}")

        
        # Step 2: Retrieve Guide
        if target_guide_no:
            print(f"\n>>> Step 2: Retrieving Response Guide {target_guide_no}...")
            demo.retrieve_guide(target_guide_no)
        
    else:
        print("    Could not identify material.")

    print("\n[FINISH] Demo completed.")

if __name__ == "__main__":
    main()
