import chromadb
from chromadb.utils import embedding_functions
import json
import re
import os
from typing import List, Dict, Any

# Configuration
DATA_DIR = "Prepared Data_CN"
DB_DIR = "erg_chroma_db_cn" # Separate DB for Chinese
INDEX_FILE = os.path.join(DATA_DIR, "ERG_Index_Processed_CN.txt")
GUIDES_FILE = os.path.join(DATA_DIR, "ERG_Guides_Cleaned_CN.txt")
GREEN_TABLE_1 = os.path.join(DATA_DIR, "green_table_1_CN.json")
GREEN_TABLE_2 = os.path.join(DATA_DIR, "green_table_2_CN.json")
GREEN_TABLE_3 = os.path.join(DATA_DIR, "green_table_3_CN.json")

# Ensure DB dir exists (chroma creates it, but good to be explicit for logging)
os.makedirs(DB_DIR, exist_ok=True)

def load_json(path: str) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_erg_index(path: str) -> List[Dict[str, Any]]:
    materials = []
    # Pattern: UN ID: 1005 corresponds to Material: Name (CN Name). Emergency Response Guide Number: 125. ...
    # Be robust to spaces
    pattern = re.compile(r"UN ID:\s*(\d{4})\s*corresponds to Material:\s*(.+?)\.\s*Emergency Response Guide Number:\s*(\d+[A-Z]?)\.")
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            match = pattern.search(line)
            if match:
                un_id, name, guide_no = match.groups()
                
                # Check for flags in the text (both EN and CN keywords)
                is_tih = "**[TIH Material]**" in line or "TIH 物質" in line
                is_polymerization = "violent polymerization" in line or "劇烈聚合反應" in line
                
                materials.append({
                    "un_id": un_id,
                    "name": name.strip(),
                    "guide_no": guide_no,
                    "is_tih": is_tih,
                    "is_polymerization": is_polymerization,
                    "full_text": line # Store the original line as the document text
                })
    return materials

def enrich_materials(materials: List[Dict], gt1: Dict, gt2: Dict, gt3_lookup: Dict) -> List[Dict]:
    enriched = []
    gt1_cnt = 0
    gt2_cnt = 0
    gt3_cnt = 0

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
        mat['table3_content'] = '' # New field for Table 3
        
        # Add Green Table 1 info (Isolation Distances)
        if un_id in gt1:
            data = gt1[un_id]
            gt1_cnt += 1
            
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
            # Assuming GT2 structure is list of objects
            # Format: [{"material_name": "...", "tih_gases": ["gas1", "gas2"]}]
            # Or dict? Check GT2 format. Usually list for same UN ID because multiple materials map to one UN.
            # But here un_id key maps to list.
            extracted_gases = []
            if isinstance(gt2[un_id], list):
                for entry in gt2[un_id]:
                    extracted_gases.extend(entry.get('tih_gases', []))
            
            mat['water_reactive_gases'] = ", ".join(list(set(extracted_gases)))
            gt2_cnt += 1
        else:
            mat['is_water_reactive'] = False
            mat['water_reactive_gases'] = ""
            
        # Add Green Table 3 info (Detailed Large Spills)
        if un_id in gt3_lookup:
            t3_data = gt3_lookup[un_id]
            gt3_cnt += 1
            
            # Format Table 3 data as text to append to full_text
            # Use Chinese labels if possible or just structure clearly
            t3_text = f"\n[詳細大量洩漏資料 (表3) 針對 {mat['name']}]\n"
            for container in t3_data.get('containers', []):
                ctype = container.get('type', 'Unknown Container')
                init_iso = container.get('initial_isolation_m', '?')
                
                day = container.get('day_km', {})
                night = container.get('night_km', {})
                
                t3_text += f"- 容器類型 (Container): {ctype}\n"
                t3_text += f"  初始隔離 (Initial Isolation): {init_iso} meters\n"
                t3_text += f"  日間防護距離 (Protective Distance Day): 低風 (Low Wind): {day.get('low_wind','?')}km, 中風 (Moderate): {day.get('moderate_wind','?')}km, 強風 (High): {day.get('high_wind','?')}km\n"
                t3_text += f"  夜間防護距離 (Protective Distance Night): 低風 (Low Wind): {night.get('low_wind','?')}km, 中風 (Moderate): {night.get('moderate_wind','?')}km, 強風 (High): {night.get('high_wind','?')}km\n"
            
            mat['table3_content'] = t3_text
            mat['full_text'] += t3_text # Append to document content for retrieval

        enriched.append(mat)
    
    print(f"Enriched Stats: GT1 matches: {gt1_cnt}, GT2 matches: {gt2_cnt}, GT3 matches: {gt3_cnt}")
    return enriched

def parse_guides(path: str) -> List[Dict[str, Any]]:
    print(f"Parsing guides from {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by "GUIDE" line
    # Since the file starts with intro text, we process it differently
    chunks = []
    seen_guides = set()
    
    # 1. Intro (Everything before first GUIDE line)
    segments = re.split(r'\nGUIDE\n', content)
    
    # First segment is Intro
    intro_text = segments[0]
    chunks.append({
        "guide_no": "000",
        "type": "intro",
        "content": intro_text.strip(),
        "combined_text": f"GUIDE 000 (Intro/General Info/如何使用): {intro_text.strip()}"
    })
    
    # Remaining segments are Guides
    for segment in segments[1:]:
        lines = segment.split('\n', 1) # Split only first newline to separate number
        if len(lines) < 2:
            continue
            
        guide_no = lines[0].strip()
        guide_body = lines[1].strip()
        
        # Valid guide Check
        if not re.match(r'^\d+[A-Z]?$', guide_no):
            # Might be some artifact, skip or log
            print(f"Warning: Skipped segment with invalid guide number: {guide_no}")
            continue
        
        # Deduplication
        if guide_no in seen_guides:
            print(f"Warning: Duplicate guide {guide_no} found. Keeping first occurrence.")
            continue
        seen_guides.add(guide_no)
            
        chunks.append({
            "guide_no": guide_no,
            "type": "guide",
            "content": guide_body,
            "combined_text": f"GUIDE {guide_no} (指南 {guide_no}):\n{guide_body}"
        })
        
    print(f"Parsed {len(chunks)} guide sections.")
    return chunks

def build_db():
    print("Initializing ChromaDB...")
    
    # Use a multilingual embedding model for better Chinese support
    # try to use sentence-transformers if possible
    print("Using multilingual-MiniLM model...")
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    
    client = chromadb.PersistentClient(path=DB_DIR)
    
    # Delete existing collection if rebuilding to stay clean
    try:
        client.delete_collection(name="erg_cn")
    except:
        pass
        
    collection = client.create_collection(name="erg_cn", embedding_function=ef)
    
    # 1. Load Green Tables
    print("Loading Green Tables...")
    gt1 = load_json(GREEN_TABLE_1)
    gt2 = load_json(GREEN_TABLE_2)
    gt3 = load_json(GREEN_TABLE_3)
    
    # Transform GT3 list to lookup dict by UN ID
    gt3_lookup = {}
    if "chemicals" in gt3:
        for chem in gt3["chemicals"]:
            # Correct key is un_number (e.g., "UN1005"). We need just "1005"
            if "un_number" in chem:
                full_un = str(chem["un_number"])
                # Extract digits
                un_digits = "".join(filter(str.isdigit, full_un))
                if un_digits:
                    gt3_lookup[un_digits] = chem # Map "1005" -> Object
    
    # 2. Parse Index (Materials)
    print("Parsing ERG Index...")
    materials = parse_erg_index(INDEX_FILE)
    print(f"Found {len(materials)} material entries.")
    
    # 3. Enrich Materials
    print("Enriching materials with Green Table data...")
    enriched_materials = enrich_materials(materials, gt1, gt2, gt3_lookup)
    
    # 4. Add Materials to Chroma
    print("Adding materials to ChromaDB...")
    
    mat_ids = []
    mat_docs = []
    mat_metas = []
    
    for idx, mat in enumerate(enriched_materials):
        mat_ids.append(f"mat_{mat['un_id']}_{idx}") # Unique ID
        mat_docs.append(mat['full_text'])
        
        # Metadata must be simple types (str, int, float, bool)
        meta = {
            "type": "material",
            "un_id": mat['un_id'],
            "name": mat['name'],
            "guide_no": mat['guide_no'],
            "is_tih": mat['is_tih'],
            "is_polymerization": mat['is_polymerization'],
            "is_water_reactive": mat['is_water_reactive'],
            "water_reactive_gases": mat.get('water_reactive_gases', ""),
            "small_iso": mat.get('small_iso', ""),
            "small_day": mat.get('small_day', ""),
            "small_night": mat.get('small_night', ""),
            "large_iso": mat.get('large_iso', ""),
            "large_day": mat.get('large_day', ""),
            "large_night": mat.get('large_night', ""),
            "large_note": mat.get('large_note', ""),
            "table3_content": mat.get('table3_content', "")
        }
        mat_metas.append(meta)
        
    # Batch add
    batch_size = 500
    for i in range(0, len(mat_ids), batch_size):
        collection.add(
            ids=mat_ids[i:i+batch_size],
            documents=mat_docs[i:i+batch_size],
            metadatas=mat_metas[i:i+batch_size]
        )
        print(f"  Added batch {i} to {i+batch_size}")

    # 5. Parse and Add Guides
    print("Parsing and Adding Guides...")
    guides = parse_guides(GUIDES_FILE)
    
    guide_ids = []
    guide_docs = []
    guide_metas = []
    
    for g in guides:
        guide_ids.append(f"guide_{g['guide_no']}")
        guide_docs.append(g['combined_text'])
        guide_metas.append({
            "type": "guide",
            "guide_no": g['guide_no']
        })
        
    collection.add(
        ids=guide_ids,
        documents=guide_docs,
        metadatas=guide_metas
    )
    print("Guides added.")

    print(f"RAG Build Complete! Database saved to '{DB_DIR}'")

if __name__ == "__main__":
    build_db()
