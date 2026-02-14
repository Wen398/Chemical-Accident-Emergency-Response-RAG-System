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
            n_results=100 # Significantly increased window to ensure short exact names (like "Chlorine") aren't crowded out by long descriptions
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
            
            # Sub-strategy: Filter candidates that actually contain the query somehow first
            # to avoid iterating irrelevant ones? No, list is small (50).
            
            # Sort candidates logic:
            # 1. Exact match preferred
            # 2. Starts with preferred
            # 3. Shorter name preferred (Occam's razor: "Chlorine" better than "Chlorine mixture")
            
            # Let's verify 'exact match' explicitly first
            for cand in candidates:
                cand_name = cand['meta']['name'].lower()
                if cand_name == query_lower:
                    best_match = cand
                    print_info(f"Match Method: Exact Name (Matched '{cand['meta']['name']}')")
                    break
            
            # Priority 3: Starts With Match (sorted by length to find shortest "Chlorine" vs "Chlorine something")
            if not best_match:
                 # Filter for starts-with matches
                 starts_with_cands = [c for c in candidates if c['meta']['name'].lower().startswith(query_lower)]
                 if starts_with_cands:
                     # Sort by length: shortest first ("Chlorine" < "Chlorine trifluoride")
                     starts_with_cands.sort(key=lambda x: len(x['meta']['name']))
                     best_match = starts_with_cands[0]
                     print_info(f"Match Method: Name Starts With (Matched '{best_match['meta']['name']}')")
        
            # Priority 4: Contains Query (but prioritize distinct word match)
            if not best_match:
                 # Look for query as a distinct word
                 import re
                 pattern = r'\b' + re.escape(query_lower) + r'\b'
                 
                 word_match_cands = []
                 for c in candidates:
                     if re.search(pattern, c['meta']['name'].lower()):
                         word_match_cands.append(c)
                 
                 if word_match_cands:
                     word_match_cands.sort(key=lambda x: len(x['meta']['name']))
                     best_match = word_match_cands[0]
                     print_info(f"Match Method: Semantic Word Match (Matched '{best_match['meta']['name']}')")
        
        # Priority 5: Fallback to Top Vector Result
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
        """Step 2: Consult the specific guide (Returning FULL CONTENT as requested)"""
        
        # FIX for Issue 2: Guide 128P -> 128
        search_guide_no = guide_no
        if guide_no.endswith('P'):
            search_guide_no = guide_no.rstrip('P')
            print_info(f"Note: Adjusting guide search from {guide_no} to {search_guide_no} (P suffix handled)")
            
        print_step(f"Agent thinking: Retrieving FULL Guide {search_guide_no} content...")
        
        # Retrieve ALL sections for the guide.
        # We assume max 5 sections per guide (usually 3: Hazards, Public Safety, Emergency Response)
        results = self.guides_col.query(
            query_texts=[specific_question], # Search text still required by API but we ignore ranking mostly
            n_results=10, 
            where={"guide_no": search_guide_no} # Strict filtering for this guide
        )
        
        if not results['ids'][0]:
            print(f"{Color.WARNING}  ⚠ Guide text not found.{Color.ENDC}")
            return
            
        # Compile full text from all retrieved chunks
        # Logic: Sort chunks by section to make sense?
        # The chunks might come back in similarity order. We should probably sort them logically.
        # Sections: POTENTIAL HAZARDS, PUBLIC SAFETY, EMERGENCY RESPONSE
        
        section_order = {
            "POTENTIAL HAZARDS": 1,
            "PUBLIC SAFETY": 2,
            "EMERGENCY RESPONSE": 3
        }
        
        # Zip documents and metadata suitable for sorting
        chunks = []
        for i in range(len(results['ids'][0])):
            chunks.append({
                "text": results['documents'][0][i],
                "section": results['metadatas'][0][i]['section']
            })
            
        # Sort based on predefined order
        chunks.sort(key=lambda x: section_order.get(x['section'], 99))
        
        print_result("Action", "Retrieved / Assembled Full Guide")
        print(f"\n{Color.BOLD}[Full Guide {search_guide_no} Content]{Color.ENDC}")
        print("------------------------------------------------")
        
        for chunk in chunks:
            print(f"{Color.BOLD}>>> {chunk['section']} <<<{Color.ENDC}")
            # Clean up the "GUIDE 123 - SECTION" header that was baked into the text if needed
            # For now just printing the raw text is fine
            clean_text = chunk['text'].replace(f"GUIDE {search_guide_no} - {chunk['section']}", "").strip()
            print(clean_text)
            print("...") # Separator
            print("")
            
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
        has_hazard = False
        
        if material_data['is_tih']:
            has_hazard = True
            print(f"  {Color.WARNING}⚠ TOXIC INHALATION HAZARD (TIH){Color.ENDC}")
            print(f"    {Color.BOLD}SMALL SPILL:{Color.ENDC}")
            print(f"      - Iso: {material_data['small_iso']}")
            print(f"      - Protect (Day): {material_data['small_day']}")
            print(f"      - Protect (Night): {material_data['small_night']}")
            
            print(f"    {Color.BOLD}LARGE SPILL:{Color.ENDC}")
            if material_data['large_note']:
                print(f"      - Note: {material_data['large_note']} (Placeholder for Table 3 integration)")
            else:
                print(f"      - Iso: {material_data['large_iso']}")
                print(f"      - Protect (Day): {material_data['large_day']}")
                print(f"      - Protect (Night): {material_data['large_night']}")
        
        if material_data['is_water_reactive']:
             has_hazard = True
             print(f"  {Color.WARNING}⚠ WATER REACTIVE MATERIAL{Color.ENDC}")
             print(f"    Produces Gases: {material_data['water_reactive_gases']}")

        if material_data['is_polymerization']:
             has_hazard = True
             print(f"  {Color.WARNING}⚠ POLYMERIZATION HAZARD{Color.ENDC}")

        if not has_hazard:
            print(f"  {Color.GREEN}✔ No special TIH/Water-Reactive/Polymerization hazards flagged.{Color.ENDC}")

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
    
    

if __name__ == "__main__":
    main()
