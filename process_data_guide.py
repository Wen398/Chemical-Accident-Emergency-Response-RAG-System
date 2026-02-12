import re

def process_guide_section(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    processed_lines = []
    
    # Manual Intro Insertion (Clean Markdown)
    intro_text = [
        "# SUGGESTED OPERATIONS SHOULD ONLY BE PERFORMED BY ADEQUATELY TRAINED AND EQUIPPED PERSONNEL",
        "",
        "## HOW TO USE THE ORANGE GUIDES",
        "",
        "### GUIDE NUMBER AND TITLE",
        "- The guide title identifies the general hazards associated with the materials in this Guide.",
        "",
        "### POTENTIAL HAZARDS",
        "- Emergency responders should consult this section first!",
        "- Describes the material hazard in terms of FIRE OR EXPLOSION and HEALTH effects upon exposure.",
        "- The primary potential hazard is listed first.",
        "- Allows the responders to make decisions to protect the emergency response team, and the surrounding population.",
        ""
    ]
    processed_lines.extend(intro_text)

    # Patterns
    page_header_pattern = re.compile(r'^--- 第 \d+ 頁 ---$')
    page_num_pattern = re.compile(r'^Page \d+$')
    erg_year_pattern = re.compile(r'^ERG 20\d{2}$')
    guide_heading_pattern = re.compile(r'^GUIDE$')
    guide_num_pattern = re.compile(r'^\d{3}$')
    bullet_pattern = re.compile(r'^\s*•\s+')
    
    # State tracking
    found_first_guide = False
    current_guide_num = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Pattern Matching for Noise
        is_noise = False
        if page_header_pattern.match(line): is_noise = True
        if page_num_pattern.match(line): is_noise = True
        if erg_year_pattern.match(line): is_noise = True
        
        if is_noise:
            i += 1
            continue
            
        # Check for GUIDE header
        if guide_heading_pattern.match(line):
            # Scan ahead for number (skipping noise)
            j = i + 1
            found_num = None
            
            while j < len(lines):
                next_line = lines[j].strip()
                # Skip noise in lookahead
                if page_header_pattern.match(next_line) or page_num_pattern.match(next_line) or erg_year_pattern.match(next_line) or next_line == "":
                    j += 1
                    continue
                
                # Check for Number
                if guide_num_pattern.match(next_line):
                    found_num = next_line
                break # Stop if we hit non-noise and non-number (found_num will be set if matched)
            
            if found_num:
                found_first_guide = True
                
                if found_num == current_guide_num:
                    # Duplicate header, skip this GUIDE block and the number line
                    # We need to skip until j+1
                    i = j + 1
                    continue
                else:
                    # New Guide
                    current_guide_num = found_num
                    processed_lines.append("") # Spacer
                    processed_lines.append("GUIDE")
                    processed_lines.append(found_num)
                    i = j + 1
                    continue
        
        if not found_first_guide:
            # Skip everything before first guide (since we inserted manual intro)
            i += 1
            continue
            
        # Normal content processing
        # Replace bullets
        clean_content = bullet_pattern.sub('- ', line)
        if clean_content:
            processed_lines.append(clean_content)
            
        i += 1

    with open(output_path, 'w', encoding='utf-8') as f:
        for line in processed_lines:
            f.write(line + '\n')

if __name__ == "__main__":
    input_file = "/home/khstudent3/chemical-accident-system/ERG_Guide_Section.txt"
    output_file = "/home/khstudent3/chemical-accident-system/ERG_Guides_Cleaned.txt"
    process_guide_section(input_file, output_file)
    print(f"Processed {input_file} to {output_file}")
