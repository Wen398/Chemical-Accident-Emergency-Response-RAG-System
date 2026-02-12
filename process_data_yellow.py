import re

def process_yellow_section(input_path, output_path):
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
    
    current_id = None
    current_guide = None
    current_name_parts = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if page_header_pattern.match(line) or page_num_pattern.match(line) or erg_year_pattern.match(line):
            continue
            
        # Check if line is new entry start
        match = entry_start_pattern.match(line)
        if match:
            # Save previous entry
            if current_id:
                full_name = " ".join(current_name_parts)
                entries.append(f"UN ID: {current_id} corresponds to Material: {full_name}. Emergency Response Guide Number: {current_guide}.")
            
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
                # Filter out table headers if any remain
                if "ID" in line and "Guide" in line:
                    continue
                current_name_parts.append(line)
    
    # Add last entry
    if current_id:
        full_name = " ".join(current_name_parts)
        entries.append(f"UN ID: {current_id} corresponds to Material: {full_name}. Emergency Response Guide Number: {current_guide}.")

    # Write sentences
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(entry + '\n')

if __name__ == "__main__":
    input_file = "/home/khstudent3/chemical-accident-system/ERG_Material_Yellow_Section.txt"
    output_file = "/home/khstudent3/chemical-accident-system/ERG_Index_Processed.txt" # We will overwrite this first
    process_yellow_section(input_file, output_file)
    print(f"Processed {input_file} to {output_file}")
