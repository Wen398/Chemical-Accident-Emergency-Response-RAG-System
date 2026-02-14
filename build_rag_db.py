import chromadb
import json
import re
import os
from typing import List, Dict, Any

# Configuration
DATA_DIR = "Prepared Data"
DB_DIR = "erg_chroma_db"
INDEX_FILE = os.path.join(DATA_DIR, "ERG_Index_Processed.txt")
GUIDES_FILE = os.path.join(DATA_DIR, "ERG_Guides_Cleaned.txt")
GREEN_TABLE_1 = os.path.join(DATA_DIR, "green_table_1.json")
GREEN_TABLE_2 = os.path.join(DATA_DIR, "green_table_2.json")

def load_json(path: str) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_erg_index(path: str) -> List[Dict[str, Any]]:
    materials = []
    # Pattern: UN ID: 1005 corresponds to Material: Ammonia, anhydrous. Emergency Response Guide Number: 125. ...
    pattern = re.compile(r"UN ID:\s*(\d{4})\s*corresponds to Material:\s*(.*?)\.\s*Emergency Response Guide Number:\s*(\d+[A-Z]?)\.")
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            match = pattern.search(line)
            if match:
                un_id, name, guide_no = match.groups()
                
                # Check for flags in the text
                is_tih = "**[TIH Material]**" in line
                is_polymerization = "violent polymerization" in line
                
                materials.append({
                    "un_id": un_id,
                    "name": name,
                    "guide_no": guide_no,
                    "is_tih": is_tih,
                    "is_polymerization": is_polymerization,
                    "full_text": line # Store the original line as the document text
                })
    return materials

def enrich_materials(materials: List[Dict], gt1: Dict, gt2: Dict) -> List[Dict]:
    enriched = []
    for mat in materials:
        un_id = mat['un_id']
        
        # Initialize defaults for Green Table 1 data
        mat['small_iso'] = ''
        mat['small_day'] = ''
        mat['small_night'] = ''
        mat['large_iso'] = ''
        mat['large_day'] = ''
        mat['large_night'] = ''
        mat['large_note'] = '' # For "Refer to Table 3"
        
        # Add Green Table 1 info (Isolation Distances)
        if un_id in gt1:
            data = gt1[un_id]
            
            # Small Spill
            if 'small_spill' in data:
                ss = data['small_spill']
                mat['small_iso'] = ss.get('isolation_distance', '')
                mat['small_day'] = ss.get('protect_day', '')
                mat['small_night'] = ss.get('protect_night', '')
                
            # Large Spill
            if 'large_spill' in data:
                ls = data['large_spill']
                if "note" in ls:
                    mat['large_note'] = ls['note']
                else:
                    mat['large_iso'] = ls.get('isolation_distance', '')
                    mat['large_day'] = ls.get('protect_day', '')
                    mat['large_night'] = ls.get('protect_night', '')
        
        # Add Green Table 2 info (Water Reactive)
        if un_id in gt2:
            mat['is_water_reactive'] = True
            mat['water_reactive_gases'] = ", ".join(gt2[un_id][0].get('tih_gases', []))
        else:
            mat['is_water_reactive'] = False
            mat['water_reactive_gases'] = ""
            
        enriched.append(mat)
    return enriched

def parse_guides(path: str) -> List[Dict[str, Any]]:
    # This parser assumes the structure seen in the sample:
    # GUIDE
    # 111
    # ... content ...
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by "GUIDE" followed by newline and number
    # Note: The split might need adjustment based on exact file format
    # Based on sample: 
    # GUIDE
    # 111
    # Guides (orange section)
    
    # Let's split by the word GUIDE at the start of a line, but we need to capture the number
    raw_guides = re.split(r'\nGUIDE\n', content)
    
    parsed_chunks = []
    
    for section in raw_guides:
        if not section.strip():
            continue
            
        lines = section.strip().split('\n')
        if not lines:
            continue
            
        # First line should be the guide number
        guide_no_match = re.match(r'^(\d+[A-Z]?)', lines[0].strip())
        if not guide_no_match:
            # Maybe it's the very first chunk which might not have the split pattern preceding it if file starts with GUIDE
            # Or it's just garbage.
            continue
            
        guide_no = guide_no_match.group(1)
        full_text = section
        
        # Split into sections: POTENTIAL HAZARDS, PUBLIC SAFETY, EMERGENCY RESPONSE
        # We will create 3 chunks per guide
        
        # Find indices
        # Note: Headers are usually uppercase. 
        # Using regex to find the start of these sections
        
        potential_hazards_idx = -1
        public_safety_idx = -1
        emergency_response_idx = -1
        
        # Helper to find line index
        for i, line in enumerate(lines):
            clean_line = line.strip()
            if clean_line == "POTENTIAL HAZARDS":
                potential_hazards_idx = i
            elif clean_line == "PUBLIC SAFETY":
                public_safety_idx = i
            elif clean_line == "EMERGENCY RESPONSE":
                emergency_response_idx = i
        
        # Extract text function
        def extract_text(start, end=None):
            if start == -1: return ""
            if end == -1: return "\n".join(lines[start:])
            return "\n".join(lines[start:end])

        # Logic to slice based on what sections exist (usually all 3 exist)
        indices = sorted([
            (potential_hazards_idx, 'POTENTIAL HAZARDS'),
            (public_safety_idx, 'PUBLIC SAFETY'),
            (emergency_response_idx, 'EMERGENCY RESPONSE')
        ], key=lambda x: x[0])
        
        # Filter out not found indices (-1)
        valid_indices = [x for x in indices if x[0] != -1]
        
        for i in range(len(valid_indices)):
            start_idx = valid_indices[i][0]
            section_name = valid_indices[i][1]
            
            end_idx = -1
            if i < len(valid_indices) - 1:
                end_idx = valid_indices[i+1][0]
                
            chunk_text = extract_text(start_idx, end_idx)
            
            parsed_chunks.append({
                "guide_no": guide_no,
                "section": section_name,
                "text": f"GUIDE {guide_no} - {section_name}\n\n{chunk_text}", # Add context to text
            })
            
    return parsed_chunks

def main():
    print("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=DB_DIR)
    
    # 1. Collection A: erg_materials
    # Delete if exists to rebuild
    try:
        client.delete_collection("erg_materials")
    except:
        pass
    
    print("Building 'erg_materials' collection...")
    materials_col = client.create_collection(name="erg_materials")
    
    # Load and process data
    print("Loading raw data...")
    materials = parse_erg_index(INDEX_FILE)
    gt1 = load_json(GREEN_TABLE_1)
    gt2 = load_json(GREEN_TABLE_2)
    
    enriched_materials = enrich_materials(materials, gt1, gt2)
    
    # Prepare batch data
    ids = []
    documents = []
    metadatas = []
    
    print(f"Ingesting {len(enriched_materials)} materials...")
    for idx, mat in enumerate(enriched_materials):
        # Create unique ID. UN ID isn't unique (one UN ID can have multiple rows/names).
        # So specific combinations might be needed, or just a simple index/uuid.
        # Format: UNID_Index
        
        doc_id = f"{mat['un_id']}_{idx}"
        ids.append(doc_id)
        documents.append(mat['full_text'])
        
        # Prepare metadata (ensure all values are str, int, float, or bool)
        meta = {
            "un_id": mat['un_id'],
            "name": mat['name'],
            "guide_no": mat['guide_no'],
            "is_tih": mat['is_tih'],
            "is_polymerization": mat['is_polymerization'],
            "is_water_reactive": mat['is_water_reactive'],
            "water_reactive_gases": mat.get('water_reactive_gases', ''),
            # Detailed Table 1 Data
            "small_iso": mat['small_iso'],
            "small_day": mat['small_day'],
            "small_night": mat['small_night'],
            "large_iso": mat['large_iso'],
            "large_day": mat['large_day'],
            "large_night": mat['large_night'],
            "large_note": mat['large_note']
        }
        metadatas.append(meta)
        
        # Batch ingest every 1000 to be safe/efficient
        if len(ids) >= 1000:
            materials_col.add(documents=documents, metadatas=metadatas, ids=ids)
            ids, documents, metadatas = [], [], []

    if ids:
        materials_col.add(documents=documents, metadatas=metadatas, ids=ids)
        
    print("Materials collection built.")
    
    # 2. Collection B: erg_guides
    try:
        client.delete_collection("erg_guides")
    except:
        pass
        
    print("Building 'erg_guides' collection...")
    guides_col = client.create_collection(name="erg_guides")
    
    print("Parsing guides...")
    guide_chunks = parse_guides(GUIDES_FILE)
    
    g_ids = []
    g_docs = []
    g_metas = []
    
    print(f"Ingesting {len(guide_chunks)} guide sections...")
    for idx, chunk in enumerate(guide_chunks):
        doc_id = f"guide_{chunk['guide_no']}_{chunk['section']}_{idx}"
        g_ids.append(doc_id)
        g_docs.append(chunk['text'])
        g_metas.append({
            "guide_no": chunk['guide_no'],
            "section": chunk['section']
        })
        
        if len(g_ids) >= 1000:
            guides_col.add(documents=g_docs, metadatas=g_metas, ids=g_ids)
            g_ids, g_docs, g_metas = [], [], []
            
    if g_ids:
        guides_col.add(documents=g_docs, metadatas=g_metas, ids=g_ids)
        
    print("Guides collection built.")
    print(f"Database saved to {os.path.abspath(DB_DIR)}")

if __name__ == "__main__":
    main()
