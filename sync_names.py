import json
import os
import re

# Paths
INPUT_DIR = "/home/khstudent3/chemical-accident-system/Prepared Data_CN"
INDEX_FILE = os.path.join(INPUT_DIR, "ERG_Index_Processed_CN.txt")
GREEN_TABLE_FILES = [
    os.path.join(INPUT_DIR, "green_table_1_CN.json"),
    os.path.join(INPUT_DIR, "green_table_2_CN.json"),
    os.path.join(INPUT_DIR, "green_table_3_CN.json")
]

def load_canonical_names():
    print("Loading canonical names from ERG Index...")
    canonical_map = {} # Key: Pure English Name, Value: Full Name (Eng + Chi)
    
    # Regex to capture "Material: English Name (Chinese Name)."
    # Pattern: ... Material: (English Name) \((Chinese Name)\)\. ...
    # Wait, the structure in file is: Material: Name (Trans). 
    # Let's be flexible.
    
    pattern = re.compile(r"Material: (.+?) \((.+?)\)\. Emergency")
    
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                eng_name = match.group(1).strip()
                chi_name = match.group(2).strip()
                full_name = f"{eng_name} ({chi_name})"
                
                # Store in map
                canonical_map[eng_name] = full_name
                
                # Also handle split names if "/" exists in English name? 
                # Index usually lists separate lines for synonyms.
                # But sometimes Green Table combines them with "/".
                
    print(f"Loaded {len(canonical_map)} canonical names from Index.")
    return canonical_map

def sync_green_tables(canonical_map):
    print("Syncing Green Tables...")
    
    for file_path in GREEN_TABLE_FILES:
        if not os.path.exists(file_path):
            print(f"Skipping {file_path} (not found)")
            continue
            
        print(f"Processing {os.path.basename(file_path)}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        modified_count = 0
        
        # Helper function to process a name string
        def standardize_name(current_full_name):
            # Extract English part of current name
            # Format is usually "Eng (Chi)"
            match = re.match(r"(.+?) \((.+?)\)", current_full_name)
            if not match:
                return current_full_name # Format doesn't match, skip
            
            eng_part = match.group(1).strip()
            current_chi = match.group(2).strip()
            
            # Special handling for names with "/" (e.g., "Ammonia... / ...")
            # If the English part in Green Table is a combination that doesn't exist in Index exactly
            if eng_part not in canonical_map:
                # Try to see if it's a slashed name
                if " / " in eng_part:
                    parts = eng_part.split(" / ")
                    # Check if ANY part exists in canonical map to get the translation?
                    # Or check if ALL parts exist?
                    # Usually if user manually edited Green Table, we might trust it BUT 
                    # user asked to use Index as authority if different.
                    
                    # Case 1: Simple match
                    pass
                return current_full_name
            
            # Check if canonical exists
            canonical_full = canonical_map.get(eng_part)
            if canonical_full and canonical_full != current_full_name:
                # Update!
                return canonical_full
            
            return current_full_name

        # Traverse JSON structure
        if "chemicals" in data and isinstance(data["chemicals"], list):
            # Table 3 style
            for chem in data["chemicals"]:
                if "name" in chem:
                    old_name = chem["name"]
                    new_name = standardize_name(old_name)
                    if new_name != old_name:
                        chem["name"] = new_name
                        modified_count += 1
        else:
            # Table 1/2 style (Dict)
            for key, entry in data.items():
                if isinstance(entry, dict):
                     if "material_name" in entry:
                        old_name = entry["material_name"]
                        new_name = standardize_name(old_name)
                        if new_name != old_name:
                            entry["material_name"] = new_name
                            modified_count += 1
                elif isinstance(entry, list):
                    # Sometimes structure is list of objects? (Green Table 2 structure in attachment looked like list)
                    for item in entry:
                         if isinstance(item, dict) and "material_name" in item:
                            old_name = item["material_name"]
                            new_name = standardize_name(old_name)
                            if new_name != old_name:
                                item["material_name"] = new_name
                                modified_count += 1

        if modified_count > 0:
            print(f"  Updated {modified_count} names in {os.path.basename(file_path)}")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        else:
            print(f"  No changes needed for {os.path.basename(file_path)}")

if __name__ == "__main__":
    canonical_names = load_canonical_names()
    sync_green_tables(canonical_names)