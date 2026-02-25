import json
import os
import re

INPUT_FILE = "Prepared Data/ERG_Guides_Cleaned.txt"
MAPPING_FILE = "guide_translation_mapping.json"
OUTPUT_FILE = "Prepared Data_CN/ERG_Guides_Cleaned_CN.txt"
OUTPUT_DIR = "Prepared Data_CN"

def apply_guide_translations():
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(MAPPING_FILE):
        print(f"Error: {MAPPING_FILE} not found.")
        return

    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    print("Loading translation mapping...")
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    # Create a normalized mapping dictionary to handle potential whitespace issues
    # Key = stripped line, Value = translation
    norm_mapping = {k.strip(): v for k, v in mapping.items()}
    
    print(f"Loaded {len(norm_mapping)} translation pairs.")

    print(f"Processing {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        
        lines = f_in.readlines()
        count_translated = 0
        
        for line in lines:
            original = line.strip()
            
            # Preserve empty lines
            if not original:
                f_out.write("\n")
                continue
            
            # 1. Try exact match from mapping
            if original in norm_mapping:
                translation = norm_mapping[original]
                
                # SPECIAL HANDLING: Fix for merged headers like "sentence. Fire"
                # If the translation ends with "Fire)" or similar header artifacts inside the bracket 
                # AND the key ended with "Fire", we might want to split it.
                # Example Key: "...as necessary. Fire"
                # Example Value: "...as necessary. Fire (...需...。火災)"
                
                # Check if the original line ends with a known header that should be on a new line
                # "Fire", "Spill or Leak", "First Aid", "Health", etc. 
                # But be careful not to match random words.
                # The "Fire" artifact usually comes after a period.
                
                # Logic: If the replacement text contains a header-like suffix inside the Chinese part, 
                # structure is usually: "Eng Text Header (Chi Text Header)"
                # We want: 
                # Eng Text (Chi Text)
                # Header (Chi Header)
                
                # This is complex to automate perfectly without a specific list of artifacts.
                # However, since the user accepted the mapping as is, maybe we just write it.
                # But I promised to handle the "Fire" case.
                
                suffix_triggers = [" Fire", " Spill or Leak", " First Aid", " Public Safety", " Emergency Response"]
                
                matched_suffix = None
                for trigger in suffix_triggers:
                    if original.endswith(trigger) and not original.endswith("Small Fire") and not original.endswith("Large Fire"): # Avoid "Small Fire" header being treated as suffix to empty? No.
                        # Check if it follows a period to be sure it's a merged sentence
                         if original.endswith("." + trigger):
                             matched_suffix = trigger
                             break
                
                if matched_suffix:
                    # It's a merged line!
                    # "Text. Fire" -> "Text. (Chi Text.)" \n "Fire (Chi Fire)"
                    # We need to look up "Fire" separately or guess.
                    
                    # 1. Remove suffix from English
                    pure_eng = original[:-len(matched_suffix)].strip()
                    header_eng = matched_suffix.strip()
                    
                    # 2. Try to split translated string?
                    # Format: "Eng. Header (Chi. ChiHeader)"
                    # Regex to extract Chinese part
                    match_chi = re.search(r"\((.+)\)$", translation)
                    if match_chi:
                        full_chi = match_chi.group(1)
                        # Assume Chinese separator corresponds? Often difficult.
                        # Simplest approach: Use the mapping for the 'pure' sentence if it exists?
                        # No, the mapping key includes the suffix.
                        
                        # Let's try to interpret the Chinese part.
                        # "火災" is likely at the end.
                        chi_header_map = {
                            "Fire": "火災",
                            "Spill or Leak": "洩漏",
                            "First Aid": "急救",
                            "Public Safety": "公共安全",
                            "Emergency Response": "緊急應變"
                        }
                        
                        chi_suffix = chi_header_map.get(header_eng)
                        if chi_suffix and full_chi.endswith(chi_suffix):
                             # Remove suffix from Chinese
                             pure_chi = full_chi[:-len(chi_suffix)].strip()
                             # Should be "Eng. (Chi.)" \n "Header (ChiHeader)"
                             
                             # Reconstruct Line 1
                             line1 = f"{pure_eng} ({pure_chi})"
                             # Reconstruct Line 2 (Header)
                             line2 = f"{header_eng} ({chi_suffix})"
                             
                             f_out.write(line1 + "\n")
                             f_out.write(line2 + "\n")
                             count_translated += 1
                             continue

                # Default case: Just write the translation from map
                f_out.write(translation + "\n")
                count_translated += 1
            
            else:
                # Not in mapping?
                # It might be a guide number (digits) or something missed.
                # Keep original.
                f_out.write(original + "\n")

    print(f"Done. Translated {count_translated} lines.")
    print(f"Output saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    apply_guide_translations()
