import re
import json

def load_tih_data(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.keys())
    except:
        return set()

def process_blue_section(input_path, output_path, tih_ids):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    entries = []
    
    # Blue section pattern regexes
    guide_id_oneline_pattern = re.compile(r'^(\d{3}P?)\s+(\d{4})$')
    guide_pattern = re.compile(r'^(\d{3}P?)$')
    id_pattern = re.compile(r'^(\d{4})$')
    embedded_guide_id_pattern = re.compile(r'^(.*?)\s+(\d{3}P?)\s+(\d{4})$')
    embedded_guide_pattern = re.compile(r'^(.*?)\s+(\d{3}P?)$')
    
    # Noise patterns
    page_header_pattern = re.compile(r'^--- 第 \d+ 頁 ---$')
    page_num_pattern = re.compile(r'^Page \d+$')
    erg_year_pattern = re.compile(r'^ERG 20\d{2}$')
    
    current_name_buffer = []
    cleaned_lines = []
    table_started = False
    
    headers = ["Guide", "No.", "ID", "Name of Material", "Guide No.", "ID No."]
    
    # First pass: clean noise
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Check for start of table (Header Detection)
        if line_stripped in headers:
            table_started = True
            
        if not table_started:
            continue
            
        if page_header_pattern.match(line_stripped) or page_num_pattern.match(line_stripped) or erg_year_pattern.match(line_stripped):
            continue
        
        if line_stripped.startswith("•") or line_stripped.startswith("--"):
            continue

        # Filter table headers rigidly
        if line_stripped in headers:
             continue
        
        # Additional cleanup for lingering intro text if table_started triggered prematurely (safety)
        # But 'table_started' works by discarding everything before the first header.
        
        cleaned_lines.append(line_stripped)
        
    i = 0
    while i < len(cleaned_lines):
        line = cleaned_lines[i]
        
        # Match Checks
        m_one = guide_id_oneline_pattern.match(line)
        m_split = False
        if not m_one and i + 1 < len(cleaned_lines):
            if guide_pattern.match(line) and id_pattern.match(cleaned_lines[i+1]):
                m_split = True
        
        m_embed_one = embedded_guide_id_pattern.match(line)
        
        m_embed_split = False
        if not m_embed_one and not m_one and not m_split and i + 1 < len(cleaned_lines):
             if embedded_guide_pattern.match(line) and id_pattern.match(cleaned_lines[i+1]):
                 m_embed_split = True
                 
        guide = None
        un_id = None
        name_part = None
        advance = 0
        
        if m_one:
            guide = m_one.group(1)
            un_id = m_one.group(2)
            advance = 1
        elif m_split:
            guide = cleaned_lines[i]
            un_id = cleaned_lines[i+1]
            advance = 2
        elif m_embed_one:
            name_part = m_embed_one.group(1)
            guide = m_embed_one.group(2)
            un_id = m_embed_one.group(3)
            # If name_part is huge, it's valid.
            advance = 1
        elif m_embed_split:
            m = embedded_guide_pattern.match(line)
            name_part = m.group(1)
            guide = m.group(2)
            un_id = cleaned_lines[i+1]
            advance = 2
            
        if guide and un_id:
             # Add name_part if it exists
             if name_part and name_part.strip():
                 current_name_buffer.append(name_part.strip())
             
             # Clean buffer
             clean_name_parts = []
             for part in current_name_buffer:
                  if "Name of Material" in part or "Guide No." in part or "ID No." in part:
                      continue
                  clean_name_parts.append(part)
             
             name = " ".join(clean_name_parts).strip()
             
             # Format Output
             if name:
                 clean_guide = guide.replace("P", "")
                 entry_str = f"Material: {name} corresponds to UN ID: {un_id}. Emergency Response Guide Number: {clean_guide}."
                 if "P" in guide:
                    entry_str += " (WARNING: This material may undergo violent polymerization if heated or involved in a fire.)"
                 if un_id in tih_ids:
                    entry_str += " **[TIH Material]**: This material is a Toxic Inhalation Hazard. Please refer to Table 1 (Green Section) for Initial Isolation and Protective Action Distances."
                 entries.append(entry_str)
             
             current_name_buffer = []
             i += advance
             continue
        
        # No match, accumulate
        current_name_buffer.append(line)
        i += 1
            
    with open(output_path, 'a', encoding='utf-8') as f:
        for entry in entries:
            f.write(entry + '\n')

if __name__ == "__main__":
    tih_set = load_tih_data("/home/khstudent3/chemical-accident-system/green_table_1.json")
    input_file = "/home/khstudent3/chemical-accident-system/ERG_Material_Blue_Section.txt"
    output_file = "/home/khstudent3/chemical-accident-system/ERG_Index_Processed.txt"
    process_blue_section(input_file, output_file, tih_set)
    print(f"Processed {input_file} to {output_file}")
