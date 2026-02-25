import os
import json
import time
import re
from deep_translator import GoogleTranslator

# Configuration
INPUT_DIR = "/home/khstudent3/chemical-accident-system/Prepared Data"
OUTPUT_DIR = "/home/khstudent3/chemical-accident-system/Prepared Data_CN"
CACHE_FILE = "translation_cache.json"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize Translator
translator = GoogleTranslator(source='auto', target='zh-TW')

# Load cache if exists
translation_cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        translation_cache = json.load(f)

def get_translation(text, retries=3):
    if not text or not text.strip():
        return ""
    
    # Check cache first
    if text in translation_cache:
        return translation_cache[text]
    
    # Perform translation
    for i in range(retries):
        try:
            translated = translator.translate(text)
            if translated:
                translation_cache[text] = translated
                return translated
        except Exception as e:
            print(f"Error translating '{text}': {e}. Retrying ({i+1}/{retries})...")
            time.sleep(1) # Wait a bit before retry
    
    return text # Return original if failed

def save_cache():
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(translation_cache, f, ensure_ascii=False, indent=2)

def process_erg_index():
    print("Processing ERG Index...")
    input_path = os.path.join(INPUT_DIR, "ERG_Index_Processed.txt")
    output_path = os.path.join(OUTPUT_DIR, "ERG_Index_Processed_CN.txt")
    
    pattern = re.compile(r"(UN ID: \d+ corresponds to Material: )(.+?)(\. Emergency Response Guide Number: .+)")
    
    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        lines = f_in.readlines()
        total = len(lines)
        
        for idx, line in enumerate(lines):
            line = line.strip()
            match = pattern.match(line)
            if match:
                prefix = match.group(1)
                material_name = match.group(2)
                suffix = match.group(3)
                
                # Check for TIH warning in suffix to avoid translating it incorrectly, 
                # though we might want to translate the warning part separately later.
                # For now, we focus on material name.
                
                cn_name = get_translation(material_name)
                
                # Also translate TIH warning if present
                tih_pattern = r"(\*\*\[TIH Material\]\*\*: )(.+)"
                tih_match = re.search(tih_pattern, suffix)
                if tih_match:
                    tih_prefix = tih_match.group(1)
                    tih_msg = tih_match.group(2)
                    cn_tih_msg = get_translation(tih_msg)
                    suffix = suffix.replace(tih_msg, f"{tih_msg} ({cn_tih_msg})")

                new_line = f"{prefix}{material_name} ({cn_name}){suffix}\n"
                f_out.write(new_line)
            else:
                f_out.write(line + "\n")
            
            if idx % 100 == 0:
                print(f"Processed {idx}/{total} lines")
                save_cache()
    save_cache()
    print("ERG Index Done.")

def process_green_tables():
    print("Processing Green Tables...")
    files = ["green_table_1.json", "green_table_2.json", "green_table_3.json"]
    
    for filename in files:
        input_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(input_path):
            continue
            
        output_path = os.path.join(OUTPUT_DIR, filename.replace(".json", "_CN.json"))
        
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Determine structure based on filename
        if filename == "green_table_3.json":
            new_chemicals = []
            if "chemicals" in data:
                total_chems = len(data["chemicals"])
                for idx, chem in enumerate(data["chemicals"]):
                    new_chem = chem.copy()
                    if "name" in chem:
                        chem_name = chem["name"]
                        cn_name = get_translation(chem_name)
                        new_chem["name"] = f"{chem_name} ({cn_name})"
                    new_chemicals.append(new_chem)
                    
                    if idx % 10 == 0:
                        print(f"Processed {idx}/{total_chems} chemicals in {filename}")
                        save_cache()
                data["chemicals"] = new_chemicals
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        
        else:
            # Handle Table 1 and 2 (Dict structure)
            new_data = {}
            total = len(data)
            count = 0
            
            for key, entry in data.items():
                if not isinstance(entry, dict):
                    # Skip metadata keys if any
                    new_data[key] = entry
                    continue

                new_entry = entry.copy()
                
                # Translate Material Name
                if "material_name" in entry:
                    mat_name = entry["material_name"]
                    cn_mat_name = get_translation(mat_name)
                    new_entry["material_name"] = f"{mat_name} ({cn_mat_name})"
                    
                # Translate Notes (if distinct from material name)
                if "large_spill" in entry and isinstance(entry["large_spill"], dict) and "note" in entry["large_spill"]:
                    note = entry["large_spill"]["note"]
                    cn_note = get_translation(note)
                    new_entry["large_spill"]["note"] = f"{note} ({cn_note})"

                new_data[key] = new_entry
                count += 1
                if count % 50 == 0:
                    print(f"Processed {count}/{total} entries in {filename}")
                    save_cache()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=4)
        
        print(f"Finished {filename}")

def process_erg_guides():
    print("Processing ERG Guides...")
    input_path = os.path.join(INPUT_DIR, "ERG_Guides_Cleaned.txt")
    output_path = os.path.join(OUTPUT_DIR, "ERG_Guides_Cleaned_CN.txt")
    
    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        # We read paragraph by paragraph (blank line separated) or line by line.
        # Line by line is safer for structure but context might be lost.
        # Given the structure, let's just translate non-empty lines and append.
        
        lines = f_in.readlines()
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                f_out.write("\n")
                continue
            
            # Simple heuristic: if line is just a number or very short, might keep as is or translate carefully
            translated = get_translation(line)
            f_out.write(f"{line}\n{translated}\n")
            
            if idx % 50 == 0:
                print(f"Processed {idx}/{len(lines)} lines")
                save_cache()

    save_cache()
    print("ERG Guides Done.")

if __name__ == "__main__":
    try:
        process_green_tables() # Do smaller files first
        # Process ERG index - limiting lines for demo/speed if needed, but here we run it.
        process_erg_index()
        # ERG Guides is very long and unstructured, might take a while.
        # Uncomment to run full process
        # process_erg_guides() 
        print("All Done!")
    except KeyboardInterrupt:
        print("Process interrupted. Saving cache...")
        save_cache()
