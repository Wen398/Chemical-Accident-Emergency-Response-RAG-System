import re

def process_blue_section(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    entries = []
    
    # Blue section pattern:
    # Name (multi-line)
    # Guide (3 digits + P) AND ID (4 digits) on same line OR separate lines
    
    guide_id_oneline_pattern = re.compile(r'^(\d{3}P?)\s+(\d{4})$')
    guide_pattern = re.compile(r'^(\d{3}P?)$')
    id_pattern = re.compile(r'^(\d{4})$')
    
    # Noise patterns
    page_header_pattern = re.compile(r'^--- 第 \d+ 頁 ---$')
    page_num_pattern = re.compile(r'^Page \d+$')
    erg_year_pattern = re.compile(r'^ERG 20\d{2}$')
    
    current_name_buffer = []
    
    # We iterate and look ahead? Or look back? 
    # Since Name -> Guide -> ID, and Name is variable length, 
    # the reliable anchor is Guide followed by ID.
    
    cleaned_lines = []
    # First pass: clean noise
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if page_header_pattern.match(line_stripped) or page_num_pattern.match(line_stripped) or erg_year_pattern.match(line_stripped):
            continue
        # Filter table headers that might appear
        if "Name of Material" in line_stripped and "Guide" in line_stripped:
            continue
            
        cleaned_lines.append(line_stripped)
        
    i = 0
    while i < len(cleaned_lines):
        # We need to look for the termination of a name block.
        # Termination 1: Current line is "Guide ID"
        # Termination 2: Current line is "Guide", Next is "ID"
        
        line = cleaned_lines[i]
        
        match_oneline = guide_id_oneline_pattern.match(line)
        
        match_split = False
        if not match_oneline and i + 1 < len(cleaned_lines):
             if guide_pattern.match(line) and id_pattern.match(cleaned_lines[i+1]):
                 match_split = True
        
        if match_oneline:
            guide = match_oneline.group(1)
            un_id = match_oneline.group(2)
            
            name = " ".join(current_name_buffer)
            if name:
                entries.append(f"Material: {name} corresponds to UN ID: {un_id}. Emergency Response Guide Number: {guide}.")
            
            current_name_buffer = []
            i += 1
            continue
            
        elif match_split:
            guide = cleaned_lines[i] # pattern matched so it's clean
            un_id = cleaned_lines[i+1]
            
            name = " ".join(current_name_buffer)
            if name:
                entries.append(f"Material: {name} corresponds to UN ID: {un_id}. Emergency Response Guide Number: {guide}.")
            
            current_name_buffer = []
            i += 2
            continue
            
        else:
            # Name part
            current_name_buffer.append(line)
            i += 1
            
    # Append to the index file (don't overwrite)
    with open(output_path, 'a', encoding='utf-8') as f:
        for entry in entries:
            f.write(entry + '\n')

if __name__ == "__main__":
    input_file = "/home/khstudent3/chemical-accident-system/ERG_Material_Blue_Section.txt"
    output_file = "/home/khstudent3/chemical-accident-system/ERG_Index_Processed.txt" # Append mode in function
    process_blue_section(input_file, output_file)
    print(f"Processed {input_file} to {output_file}")
