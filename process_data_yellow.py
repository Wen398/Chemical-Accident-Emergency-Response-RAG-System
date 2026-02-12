import re
import json

def load_tih_data(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.keys()) # Return set of IDs
    except Exception as e:
        print(f"Warning: Could not load TIH data: {e}")
        return set()

def process_yellow_section(input_path, output_path, tih_ids):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    entries = []
    
    # Pattern: ID (4 digits) + space + Guide (3 digits + optional P) + optional Name on same line
    # Example: 1017 124 Chlorine
    # Example: 1010 116P Butadienes, stabilized
    entry_start_pattern = re.compile(r'^(\d{4})\s+(\d{3}P?)(?:\s+(.*))?$')
    
    # Noise patterns
    page_header_pattern = re.compile(r'^--- 第 \d+ 頁 ---$')
    page_num_pattern = re.compile(r'^Page \d+$')
    erg_year_pattern = re.compile(r'^ERG 20\d{2}$') # ERG 2024
    
    # Filter header lines that contain column titles
    header_keywords = ["Name of Material", "Guide", "No.", "ID"]
    
    current_id = None
    current_guide = None
    current_name_parts = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if page_header_pattern.match(line) or page_num_pattern.match(line) or erg_year_pattern.match(line):
            continue
            
        # Check for table header noise
        # The PDF text has headers split across lines like "Guide" \n "No."
        # So we filter exact matches or parts.
        if line in ["Guide", "No.", "ID", "Name of Material", "ID No.", "Guide No."]:
            continue
        if any(keyword in line for keyword in ["Name of Material", "Guide No.", "ID No."]):
             continue

        # Check if line is new entry start
        match = entry_start_pattern.match(line)
        if match:
            # Save previous entry
            if current_id:
                full_name = " ".join(current_name_parts)
                # Formulate the sentence
                entry_str = f"UN ID: {current_id} corresponds to Material: {full_name}. Emergency Response Guide Number: {current_guide}."
                
                # Check for Polymerization
                if "P" in current_guide:
                    entry_str += " (WARNING: This material may undergo violent polymerization if heated or involved in a fire.)"
                
                # Check for TIH
                if current_id in tih_ids:
                    entry_str += " **[TIH Material]**: This material is a Toxic Inhalation Hazard. Please refer to Table 1 (Green Section) for Initial Isolation and Protective Action Distances."
                
                entries.append(entry_str)
            
            # Start new entry
            current_id = match.group(1)
            current_guide = match.group(2)
            name_rest = match.group(3)
            current_name_parts = []
            if name_rest:
                current_name_parts.append(name_rest.strip())
        else:
            # It's part of the name
            if current_id: # Only if we have started tracking an entry
                current_name_parts.append(line)
    
    # Add last entry
    if current_id:
        full_name = " ".join(current_name_parts)
        entry_str = f"UN ID: {current_id} corresponds to Material: {full_name}. Emergency Response Guide Number: {current_guide}."
        if "P" in current_guide:
            entry_str += " (WARNING: This material may undergo violent polymerization if heated or involved in a fire.)"
        if current_id in tih_ids:
            entry_str += " **[TIH Material]**: This material is a Toxic Inhalation Hazard. Please refer to Table 1 (Green Section) for Initial Isolation and Protective Action Distances."
        entries.append(entry_str)

    # Write sentences
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(entry + '\n')

if __name__ == "__main__":
    tih_set = load_tih_data("/home/khstudent3/chemical-accident-system/green_table_1.json")
    input_file = "/home/khstudent3/chemical-accident-system/ERG_Material_Yellow_Section.txt"
    output_file = "/home/khstudent3/chemical-accident-system/ERG_Index_Processed.txt" # We will overwrite this first
    process_yellow_section(input_file, output_file, tih_set)
    print(f"Processed {input_file} to {output_file}")
