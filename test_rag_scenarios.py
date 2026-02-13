import chromadb
import sys
import time
from typing import Optional

# Configuration
DB_DIR = "erg_chroma_db"

class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_step(msg):
    print(f"{Color.CYAN}➤ {msg}{Color.ENDC}")

def print_result(key, value):
    print(f"  {Color.GREEN}✔ {key}:{Color.ENDC} {value}")

def print_info(msg):
    print(f"  ℹ {msg}")

class ERG_Agent_Tester:
    def __init__(self):
        print(f"{Color.HEADER}Initializing ERG RAG System Wrapper...{Color.ENDC}")
        self.client = chromadb.PersistentClient(path=DB_DIR)
        self.materials_col = self.client.get_collection("erg_materials")
        self.guides_col = self.client.get_collection("erg_guides")
        print(f"{Color.HEADER}System Ready.\n{Color.ENDC}")

    def search_material(self, query: str):
        """Step 1: Identify the material and its properties"""
        print_step(f"Agent thinking: Identifying material from query '{query}'...")
        
        start_time = time.time()
        
        # Strategy:
        # 1. First, try an exact name match using metadata filtering (Highest Precision)
        # 2. If no exact match, use vector semantic search (Fuzzy / Semantic Match)
        
        # Attempt 1: Exact Name Match (Case-insensitive)
        # Note: ChromaDB basic filtering is case-sensitive usually. 
        # Since we stored names as they appear, we might need a more flexible approach for "exactish" match 
        # if we can't normalize everything. 
        # But let's assume for now we try semantic search with a higher 'n_results' 
        # and then filter in Python for exact matches or high similarity.
        
        results = self.materials_col.query(
            query_texts=[query],
            n_results=5 # Fetch top 5 candidates to refine
        )
        elapsed = time.time() - start_time
        
        if not results['ids'][0]:
            print(f"{Color.FAIL}  ✖ Material not found.{Color.ENDC}")
            return None

        candidates = []
        for i in range(len(results['ids'][0])):
            candidates.append({
                'meta': results['metadatas'][0][i],
                'dist': results['distances'][0][i] if results['distances'] else 0,
                'text': results['documents'][0][i]
            })

        # Refinement Logic:
        # Check if any candidate name contains the query string (case-insensitive) strictly
        # or if the query IS the UN ID.
        
        best_match = None
        
        # Priority 1: UN ID Match
        for cand in candidates:
            if str(cand['meta']['un_id']) == query.strip():
                best_match = cand
                print_info("Match Method: Exact UN ID")
                break
        
        # Priority 2: Exact Name Match (Case Insensitive)
        if not best_match:
            query_lower = query.lower().strip()
            for cand in candidates:
                # We check if the query matches the material name or is a significant substring
                # e.g. "Chlorine" should match "Chlorine" or "Chlorine, liquid"
                # but maybe not "Calcium hypochlorite..." immediately if a better match exists.
                
                mat_name = cand['meta']['name'].lower()
                
                # Perfect match
                if mat_name == query_lower:
                    best_match = cand
                    print_info("Match Method: Exact Name")
                    break
                    
                # Split name match (e.g. "Chlorine" matches "Chlorine" part of "Chlorine")
                # This is tricky. "Chlorine" is in "Calcium hypochlorite" too? No, "chlorine" is.
                # Let's enforce that the name STARTS with the query or equals it, often a good heuristic.
                if mat_name.startswith(query_lower + ",") or mat_name.startswith(query_lower + " "):
                     if not best_match: best_match = cand # Keep looking for exact, but hold this
        
        # Priority 3: Fallback to Top Vector Result
        if not best_match:
            print_info("Match Method: Vector Similarity (Top 1)")
            best_match = candidates[0]

        meta = best_match['meta']
        
        # Simulate "Reading" the data
        print_result("Matched Material", f"{meta['name']} (UN: {meta['un_id']})")
        print_result("Guide No", meta['guide_no'])
        print_result("Agent Confidence", f"High (Found in {elapsed:.4f}s)")
        
        return meta

    def consult_guide(self, guide_no: str, specific_question: str):
        """Step 2: Consult the specific guide for a question"""
        print_step(f"Agent thinking: Checking Guide {guide_no} regarding '{specific_question}'...")
        
        results = self.guides_col.query(
            query_texts=[specific_question],
            n_results=1,
            where={"guide_no": guide_no} # Contextual Filtering
        )
        
        if not results['ids'][0]:
            print(f"{Color.WARNING}  ⚠ No specific text found in guide.{Color.ENDC}")
            return
            
        doc_text = results['documents'][0][0]
        section = results['metadatas'][0][0]['section']
        
        print_result("Relevant Section", section)
        print(f"\n{Color.BOLD}[Guide Content Snippet]{Color.ENDC}")
        print("------------------------------------------------")
        print(doc_text[:600] + ("..." if len(doc_text) > 600 else ""))
        print("------------------------------------------------\n")

    def run_scenario(self, title: str, material_query: str, guide_query: Optional[str] = None):
        print(f"{Color.BOLD}{Color.UNDERLINE}SCENARIO: {title}{Color.ENDC}")
        print("------------------------------------------------")
        
        # 1. Material Look up
        material_data = self.search_material(material_query)
        if not material_data:
            print("\n")
            return

        # 2. Check for Critical Hazards (Metadata Logic)
        print_info("Checking Critical Hazards...")
        
        if material_data['is_tih']:
            print(f"  {Color.WARNING}⚠ TOXIC INHALATION HAZARD{Color.ENDC}")
            print(f"    Small Spill Isolation: {material_data['small_spill_isolation']}")
            print(f"    Large Spill Isolation: {material_data['large_spill_isolation']}")
        
        if material_data['is_water_reactive']:
             print(f"  {Color.WARNING}⚠ WATER REACTIVE MATERIAL{Color.ENDC}")
             print(f"    Produces Gases: {material_data['water_reactive_gases']}")

        if material_data['is_polymerization']:
             print(f"  {Color.WARNING}⚠ POLYMERIZATION HAZARD{Color.ENDC}")

        # 3. Guide Consultation (if needed)
        if guide_query:
            self.consult_guide(material_data['guide_no'], guide_query)
        else:
            print_info("No specific operational question asked. Standing by.")
        
        print("\n")

def main():
    tester = ERG_Agent_Tester()
    
    # --- Scenario 1: Standard Lookup ---
    tester.run_scenario(
        title="1. General Fire Response (Standard Material)",
        material_query="Gasoline", 
        guide_query="What kind of extinguisher should I use for fire?"
    )

    # --- Scenario 2: Toxic Inhalation Hazard (TIH) ---
    tester.run_scenario(
        title="2. Toxic Gas Leak (TIH Data Retrieval)",
        material_query="Chlorine", 
        guide_query="First aid steps for inhalation"
    )

    # --- Scenario 3: Water Reactive Material ---
    tester.run_scenario(
        title="3. Water Reactive Check (Green Table 2)",
        material_query="Trichlorosilane", # Known water reactive
        guide_query="Can I use water to put out the fire?"
    )
    
    # --- Scenario 4: Polymerization Hazard ---
    tester.run_scenario(
        title="4. Polymerization Hazard Check",
        material_query="Styrene monomer", 
        guide_query="Safety precautions"
    )

    # --- Scenario 5: Evacuation (General) ---
    tester.run_scenario(
        title="5. Public Safety & Evacuation",
        material_query="Propane",
        guide_query="Evacuation distance for fire"
    )

    # --- Scenario 6: Fuzzy/Unknown Search ---
    tester.run_scenario(
        title="6. Fuzzy Search (Handling Typo)",
        material_query="Amonia" # Intentionally misspelled (Ammonia)
    )

    # --- Scenario 7: Exact vs Partial Match Test (Chlorine Fix) ---
    tester.run_scenario(
        title="7. Exact Name Match Priority",
        material_query="Chlorine", 
        guide_query="Health hazards"
    )

    # --- Scenario 8: Search by UN ID ---
    tester.run_scenario(
        title="8. Search by UN ID Directly",
        material_query="1017",  # Chlorine's ID
        guide_query="Fire explosion hazards"
    )

    # --- Scenario 9: Complex Logic - Multiple Hazards ---
    # Testing a material that might have multiple dangerous properties
    tester.run_scenario(
        title="9. Multi-Hazard Material (Hydrazine)", 
        material_query="Hydrazine, anhydrous",
        guide_query="Spill response"
    )

    # --- Scenario 10: Distinguishing Similar Names ---
    # Testing distinguish between 'Butane' and 'Butadienes'
    tester.run_scenario(
        title="10. Similar Name Disambiguation",
        material_query="Butane",
        guide_query="Fire fighting"
    )

if __name__ == "__main__":
    main()
