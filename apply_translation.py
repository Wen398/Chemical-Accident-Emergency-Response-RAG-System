import json
import os
import re

# Configuration
INPUT_DIR = "/home/khstudent3/chemical-accident-system/Prepared Data"
OUTPUT_DIR = "/home/khstudent3/chemical-accident-system/Prepared Data_CN"
MAPPING_FILE = "translation_mapping.json"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_mapping():
    if not os.path.exists(MAPPING_FILE):
        print(f"Error: {MAPPING_FILE} not found.")
        return {}
    
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def apply_translation_to_index(mapping):
    print("Applying translation to ERG Index...")
    input_path = os.path.join(INPUT_DIR, "ERG_Index_Processed.txt")
    output_path = os.path.join(OUTPUT_DIR, "ERG_Index_Processed_CN.txt")
    
    # Regex patterns
    pattern_index = re.compile(r"(UN ID: .+? corresponds to Material: )(.+?)(\. Emergency Response Guide.+)")
    pattern_tih = re.compile(r"(\*\*\[TIH Material\].+)")
    pattern_warning = re.compile(r"(Guide Number: \S+\. )(\(WARNING: .+?\))")

    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        lines = f_in.readlines()
        total = len(lines)
        
        for idx, line in enumerate(lines):
            line = line.strip()
            new_line = line
            
            # 1. Translate Material Name
            match_name = pattern_index.match(line)
            if match_name:
                prefix = match_name.group(1)
                material_name = match_name.group(2).strip()
                suffix = match_name.group(3)
                
                # Look up translation
                # Try exact match first
                cn_name = mapping.get(material_name)
                
                # If exact match fails, it might be due to subtle whitespace or special chars
                if not cn_name:
                     # Fallback: try stripping or simple normalization if needed
                     pass

                if cn_name and cn_name != material_name:
                    # Construct new line: Material Name (translated name)
                    # NOTE: The mapping file might already contain the format "English (Chinese)" or just "Chinese"
                    # We need to check to avoid double concatenation "Name (Name (Chinese))"
                    
                    if "(" in cn_name and ")" in cn_name and material_name in cn_name:
                         # Mapping is likely "Eng (Chi)" already
                         new_material_part = cn_name
                    else:
                         # Mapping is just "Chi", so we append format
                         new_material_part = f"{material_name} ({cn_name})"
                    
                    new_line = f"{prefix}{new_material_part}{suffix}"
            
            # 2. Translate TIH Warning (if present in the line)
            match_tih = pattern_tih.search(new_line)
            if match_tih:
                tih_text = match_tih.group(1).strip()
                cn_tih = mapping.get(tih_text)
                if cn_tih and cn_tih != tih_text:
                    new_line = new_line.replace(tih_text, cn_tih) # Direct replacement since usually long warning text

            # 3. Translate Polymerization Warning (if present)
            match_warning = pattern_warning.search(new_line)
            if match_warning:
                warning_text = match_warning.group(2).strip()
                cn_warning = mapping.get(warning_text)
                if cn_warning and cn_warning != warning_text:
                     new_line = new_line.replace(warning_text, cn_warning)

            f_out.write(new_line + "\n")
            
            if idx % 1000 == 0:
                print(f"Processed {idx}/{total} lines")

    print("ERG Index Done.")

def apply_translation_to_green_tables(mapping):
    print("Applying translation to Green Tables...")
    files = ["green_table_1.json", "green_table_2.json", "green_table_3.json"]
    
    for filename in files:
        input_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(input_path): continue
            
        output_path = os.path.join(OUTPUT_DIR, filename.replace(".json", "_CN.json"))
        
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Helper to translate text safely
        def translate_text(text):
            if not text: return text
            text = text.strip()
            # If mapping has it, use it
            if text in mapping:
                val = mapping[text]
                # Check if mapping already includes English to avoid duplication
                if "(" in val and ")" in val and text in val:
                    return val
                return f"{text} ({val})"
            return text

        if filename == "green_table_3.json":
            if "chemicals" in data:
                for chem in data["chemicals"]:
                    if "name" in chem:
                        chem["name"] = translate_text(chem["name"])
        else:
            # Table 1 & 2
            new_data = {}
            for key, entry in data.items():
                if isinstance(entry, dict):
                    # Material Name
                    if "material_name" in entry:
                        entry["material_name"] = translate_text(entry["material_name"])
                    
                    # Notes
                    if "large_spill" in entry and isinstance(entry["large_spill"], dict) and "note" in entry["large_spill"]:
                         # Notes might be long sentences, check if in mapping
                         note = entry["large_spill"]["note"]
                         # Often notes are TIH warnings or similar standard phrases
                         if note in mapping:
                             entry["large_spill"]["note"] = mapping[note] # Direct replace if it's a long sentence mapping
                         else:
                             # Try to translate
                             pass 
                new_data[key] = entry
            data = new_data
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Finished {filename}")

if __name__ == "__main__":
    mapping = load_mapping()
    if mapping:
        apply_translation_to_index(mapping)
        apply_translation_to_green_tables(mapping)
        print("All translations applied successfully!")
