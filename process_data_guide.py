import re

def process_guide_section(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    clean_lines = []
    current_guide = None
    buffer = []

    # Regex patterns for noise
    page_header_pattern = re.compile(r'^--- 第 \d+ 頁 ---$') # --- 第 1 頁 ---
    page_num_pattern = re.compile(r'^Page \d+$') # Page 148
    erg_year_pattern = re.compile(r'^ERG 20\d{2}$') # ERG 2024
    guide_heading_pattern = re.compile(r'^GUIDE$')
    guide_num_pattern = re.compile(r'^\d{3}$')

    skip_next = False

    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines if needed, but keeping paragraph breaks is good.
        # However, extreme empty lines from removal should be handled.
        
        if page_header_pattern.match(line):
            continue
        if page_num_pattern.match(line):
            continue
        if erg_year_pattern.match(line):
            continue
            
        # Detect GUIDE header
        # Pattern in text: 
        # GUIDE
        # 111
        if guide_heading_pattern.match(line):
            # Check next line for number
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if guide_num_pattern.match(next_line):
                    # It is a header.
                    # We might want to unify it: "GUIDE 111"
                    # But the loop will process next_line next.
                    # Let's just output "GUIDE" and let next line be "111".
                    # Or better, combine them for clarity?
                    # Let's keep structure but ensure clean breaks.
                    pass
        
        clean_lines.append(line)

    # Post-processing to join paragraphs or fixing weird breaks?
    # For now, just dumping the filtered lines is a huge improvement.
    # But let's look at the structure "GUIDE \n 111".
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for line in clean_lines:
            if line: # Write non-empty lines, or keep empty lines?
                # RAG chunks often rely on double \n for splitting.
                # Original file has gaps.
                f.write(line + '\n')
            else:
                f.write('\n')

if __name__ == "__main__":
    input_file = "/home/khstudent3/chemical-accident-system/ERG_Guide_Section.txt"
    output_file = "/home/khstudent3/chemical-accident-system/ERG_Guides_Cleaned.txt"
    process_guide_section(input_file, output_file)
    print(f"Processed {input_file} to {output_file}")
