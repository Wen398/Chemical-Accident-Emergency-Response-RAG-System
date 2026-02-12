import json
import re
import sys

def parse_txt_to_json(txt_path, output_json_path):
    # Regex patterns
    id_pattern = re.compile(r'^\d{4}$')
    guide_pattern = re.compile(r'^\d{3}P?$')
    
    # Check for data line (starts with digit or "Refer")
    # 30 m, 0.1 km, (100 ft) -> starts with digit or (
    # Refer to Table 3 -> starts with R
    data_start_pattern = re.compile(r'^(?:\d|\(|Refer)', re.IGNORECASE)
    
    # Specific ignore patterns (headers/footers)
    ignore_patterns = [
        re.compile(r'^Page \d+$', re.IGNORECASE),
        re.compile(r'^TABLE 1.*', re.IGNORECASE),
        re.compile(r'^SMALL SPILLS', re.IGNORECASE), # prefix match
        re.compile(r'^LARGE SPILLS', re.IGNORECASE),
        re.compile(r'^ID\s*No\.?$', re.IGNORECASE),
        re.compile(r'^Guide\s*No\.?$', re.IGNORECASE),
        re.compile(r'^Name of Material$', re.IGNORECASE),
        re.compile(r'^First\s*ISOLATE.*', re.IGNORECASE),
        re.compile(r'^Then\s*PROTECT.*', re.IGNORECASE),
        re.compile(r'^DAY$', re.IGNORECASE),
        re.compile(r'^NIGHT$', re.IGNORECASE),
        re.compile(r'^Meters$', re.IGNORECASE),
        re.compile(r'^\(Feet\)$', re.IGNORECASE),
        re.compile(r'^Kilometers.*', re.IGNORECASE),
        re.compile(r'^—$', re.IGNORECASE), # Dash
        re.compile(r'^\(From a.*', re.IGNORECASE), # (From a small package...)
    ]
    
    def is_noise(line):
        for pat in ignore_patterns:
            if pat.match(line):
                return True
        return False

    entries = {}
    
    # State
    current_id = None
    current_guide = None
    name_buffer = []
    data_buffer = []
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    def save_current_entry():
        nonlocal current_id, current_guide, name_buffer, data_buffer
        if current_id and current_guide:
            # Clean Name Buffer
            # 1. Remove strict duplicates
            unique_names = []
            for n in name_buffer:
                if n not in unique_names:
                    unique_names.append(n)
            
            # 2. Check for substring relationships
            # Keep only names that are NOT substrings of other names in the list
            final_names = []
            for n1 in unique_names:
                is_substring = False
                for n2 in unique_names:
                    if n1 != n2 and n1.lower() in n2.lower():
                        is_substring = True
                        break
                if not is_substring:
                    final_names.append(n1)
            
            # Handle standard "Anhydrous ammonia" vs "Ammonia, anhydrous" case if needed.
            # But usually they are distinct phrases. 
            # "Ammonia, anhydrous" is NOT a substring of "Anhydrous ammonia".
            # So both will be kept. 
            # Ideally join with " / "
            
            full_name = " / ".join(final_names).strip()
            
            # Process Data
            full_data_str = " ".join(data_buffer)
            
            # Extract items
            # 1. Distances: Value Unit (Value Unit)
            # Regex to capture "30 m (100 ft)"
            # Note: Sometimes there are spaces like "30 m ( 100 ft )"
            
            # Let's normalize spaces
            normalized_data = re.sub(r'\s+', ' ', full_data_str)
            
            # Regex for pair: \d+(\.\d+)?\s*(m|km)\s*\(\d+(\.\d+)?\s*(ft|mi)\)
            pair_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(m|km)\s*\(\s*(\d+(?:\.\d+)?)\s*(ft|mi)\s*\)')
            
            # Find all pairs
            pairs = []
            
            # We also need to handle "Refer to Table 3"
            # It might appear instead of a pair?
            # It usually appears for Large Spills.
            
            # Let's split by "Refer to Table 3" if present
            # Format: Small_Iso Small_Day Small_Night [Large_Iso|Refer] [Large_Day] [Large_Night]
            
            extracted_items = []
            
            cursor = 0
            while cursor < len(normalized_data):
                # Skip spaces
                if normalized_data[cursor] == ' ':
                    cursor += 1
                    continue
                
                # Check for "Refer to Table 3"
                if normalized_data[cursor:].lower().startswith("refer to table 3"):
                    extracted_items.append("Refer to Table 3")
                    cursor += len("Refer to Table 3")
                    continue
                
                # Check for Pair
                match = pair_pattern.match(normalized_data[cursor:])
                if match:
                    # Reconstruct readable string: "30 m (100 ft)"
                    val1, unit1, val2, unit2 = match.groups()
                    item_str = f"{val1} {unit1} ({val2} {unit2})"
                    extracted_items.append(item_str)
                    cursor += len(match.group(0))
                    continue
                
                # If neither, consume one char? (Should not happen ideally)
                cursor += 1
            
            entry = {
                "guide_no": current_guide,
                "material_name": full_name,
                "small_spill": {},
                "large_spill": {}
            }
            
            # Map Items
            if len(extracted_items) >= 1: entry["small_spill"]["isolation_distance"] = extracted_items[0]
            if len(extracted_items) >= 2: entry["small_spill"]["protect_day"] = extracted_items[1]
            if len(extracted_items) >= 3: entry["small_spill"]["protect_night"] = extracted_items[2]
            
            if len(extracted_items) >= 4:
                if extracted_items[3] == "Refer to Table 3":
                    entry["large_spill"]["note"] = "Refer to Table 3"
                else:
                    entry["large_spill"]["isolation_distance"] = extracted_items[3]
            
            if len(extracted_items) >= 5: entry["large_spill"]["protect_day"] = extracted_items[4]
            if len(extracted_items) >= 6: entry["large_spill"]["protect_night"] = extracted_items[5]
            
            entries[current_id] = entry
            
            # Reset
            current_id = None
            current_guide = None
            name_buffer = []
            data_buffer = []

    for line in lines:
        line = line.strip()
        if not line: continue
        
        # ID Detection
        if id_pattern.match(line):
            # If we are already building this ID, ignore (duplicate)
            if current_id == line:
                continue
            
            # If we have a previous entry pending, save it
            if current_id:
                save_current_entry()
            
            current_id = line
            continue
            
        # If we don't have an ID yet, ignore line (header noise before first entry)
        if not current_id:
            continue
            
        # Guide Detection
        if guide_pattern.match(line):
            if current_guide == line:
                continue # Duplicate
            # If we already have a guide, and this is a diff guide?
            # 1005... 125... 125...
            # If we have guide but no name yet, maybe it's just a correction?
            current_guide = line
            continue
            
        # Data Detection (Values)
        is_data = data_start_pattern.match(line)
        
        # If matches noise patterns, skip
        if is_noise(line):
            continue
            
        if is_data:
            data_buffer.append(line)
        else:
            # Assume part of Name
            # But wait, logic: Name comes before Data.
            # If we already have data, and we see text -> Could be next entry Name?
            # NO, next entry must start with ID.
            # So if we see text after data started... maybe multiline footnote?
            # But the structure is rigid.
            # Let's assume text after Data starts is likely noise or invalid.
            # ACTUALLY: "Ammonia, anhydrous" might be split?
            # "Ammonia,"
            # "anhydrous"
            # Both are text.
            # Data hasn't started yet.
            
            if not data_buffer:
                # Add check to avoid duplicates in name buffer
                if line not in name_buffer:
                     name_buffer.append(line)
            else:
                # We have data, but encountered text that is not ID and not Guide and not Data pattern.
                # Could be noise that slipped through?
                # e.g "See Table 3" vs "Refer to Table 3"
                # Or just garbage.
                pass

    # Save last
    if current_id:
        save_current_entry()

    # Output
    print(f"Total entries extracted: {len(entries)}")
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)
        
if __name__ == "__main__":
    parse_txt_to_json("TIH_Table1.txt", "green_table_1.json")
