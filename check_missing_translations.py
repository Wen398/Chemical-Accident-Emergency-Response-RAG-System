import json
import os
import re

# Paths
MAPPING_FILE = "translation_mapping.json"
UNIQUE_TERMS_FILE = "unique_materials_to_translate.txt"
MISSING_OUTPUT = "missing_translations.txt"

def check_missing():
    # Load the JSON mapping
    if not os.path.exists(MAPPING_FILE):
        print(f"Error: {MAPPING_FILE} not found.")
        return

    try:
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        mapped_keys = set(mapping.keys())
        print(f"Items in JSON mapping: {len(mapped_keys)}")
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    # Re-extract the expected terms (using the logic from extract_unique_terms.py) to be sure
    # Or just read the txt file if we trust it. Let's re-extract to be safe and independent.
    
    unique_terms = set()
    INPUT_DIR = "/home/khstudent3/chemical-accident-system/Prepared Data"
    
    # Logic copied from extract_unique_terms.py (the fixed version)
    pattern_index = re.compile(r"Material: (.+?)\. Emergency Response Guide")
    pattern_tih = re.compile(r"(\*\*\[TIH Material\].+)")
    pattern_warning = re.compile(r"Guide Number: \S+\. (\(WARNING: .+?\))")

    # Index File
    index_path = os.path.join(INPUT_DIR, "ERG_Index_Processed.txt")
    with open(index_path, 'r', encoding='utf-8') as f:
        for line in f:
            match_name = pattern_index.search(line)
            if match_name:
                raw_name = match_name.group(1).strip()
                if "corresponds to UN ID" not in raw_name:
                    unique_terms.add(raw_name)
            
            match_tih = pattern_tih.search(line)
            if match_tih: unique_terms.add(match_tih.group(1).strip())
            
            match_warning = pattern_warning.search(line)
            if match_warning: unique_terms.add(match_warning.group(1).strip())

    # Green Tables
    for filename in ["green_table_1.json", "green_table_2.json", "green_table_3.json"]:
        file_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(file_path): continue
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            if "chemicals" in data and isinstance(data["chemicals"], list):
                 for item in data["chemicals"]:
                    if "name" in item: unique_terms.add(item["name"].strip())
            else:
                for key, val in data.items():
                    if isinstance(val, dict):
                        if "material_name" in val: unique_terms.add(val["material_name"].strip())
                        if "large_spill" in val and isinstance(val["large_spill"], dict) and "note" in val["large_spill"]:
                             unique_terms.add(val["large_spill"]["note"].strip())

    print(f"Items expected (from source files): {len(unique_terms)}")

    # Find difference
    missing = unique_terms - mapped_keys
    
    if missing:
        print(f"Found {len(missing)} missing items!")
        with open(MISSING_OUTPUT, 'w', encoding='utf-8') as f:
            for item in sorted(list(missing)):
                f.write(item + "\n")
        print(f"Missing items written to: {MISSING_OUTPUT}")
    else:
        print("No items missing! The JSON covers all terms found in the source files.")

if __name__ == "__main__":
    check_missing()