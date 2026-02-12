import json
import re

def reverse_string_content(s):
    # Reverse the string
    # Map brackets () -> )(
    rev = s[::-1]
    return rev.translate(str.maketrans("()", ")("))

def process_table_3(txt_path, output_json_path):
    entries = {}
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        # Read lines and strip trailing newlines but match logic
        raw_lines = [l.rstrip('\n') for l in f.readlines()]
        
    # Reverse processing for text content
    processed_lines = []
    for l in raw_lines:
        rev_l = reverse_string_content(l).strip()
        processed_lines.append(rev_l)
        
    final_output = {}

    idx = 0
    un_pattern = re.compile(r'UN(\d{4})')
    data_pattern = re.compile(r'^\d') 
    
    current_id = None
    current_name = None
    data_buffer = [] 
    
    def identify_container(line_text):
        lower = line_text.lower()
        if "rail" in lower and "tank" in lower: return "Rail tank car"
        if "highway" in lower or "trailer" in lower: return "Highway tank truck or trailer"
        if "agricultural" in lower or "nurse" in lower: return "Agricultural nurse tank"
        if "cylinder" in lower: return "Multiple cylinders"
        return None

    while idx < len(processed_lines):
        line = processed_lines[idx]
        
        # 1. Check for UN ID
        un_match = un_pattern.search(line)
        if un_match:
            new_id = un_match.group(1)
            
            name_parts = []
            k = 1
            while k <= 6 and (idx - k) >= 0:
                prev = processed_lines[idx - k]
                if identify_container(prev) or data_pattern.match(prev) or "Page" in prev or "TABLE" in prev:
                    break
                if un_pattern.search(prev):
                    break
                
                if "TRANSPORT" in prev or "Large Spills" in prev or "CONTAINER" in prev:
                    pass 
                elif not prev.strip():
                    pass
                else:
                    name_parts.insert(0, prev) 
                k += 1
            
            full_name = " ".join(name_parts)
            full_name = full_name.replace(":", "").replace("/", " ").replace(",", "").strip() # Clean
            
            # Simple dedup tokens
            tokens = full_name.split()
            seen = set()
            clean_tokens = []
            for t in tokens:
                if t.lower() in ["spills", "large", "transport", "container"]:
                    continue
                if t.lower() not in seen:
                    clean_tokens.append(t)
                    seen.add(t.lower())
            current_name = " ".join(clean_tokens)
            current_id = new_id
            
            if current_id not in final_output:
                final_output[current_id] = {
                    "material_name": current_name,
                    "large_spill_details": {}
                }
            
            data_buffer = [] 
            idx += 1
            continue

        # 2. Accumulate Data or Detect Container
        if current_id:
            cont_type = identify_container(line)
            if cont_type:
                valid_data = [d for d in data_buffer if data_pattern.match(d)]
                
                # We expect 14 lines (7 pairs)
                if len(valid_data) >= 14:
                    
                    def combine(met, imp):
                        if "(" in met and "(" not in imp:
                            met, imp = imp, met
                        return f"{met} {imp}"

                    # Top-Down Indices (Highest Negative is Top)
                    # -14: Top line
                    # -1: Bottom line
                    
                    iso = combine(valid_data[-1], valid_data[-2])
                    day_low = combine(valid_data[-3], valid_data[-4])
                    day_mod = combine(valid_data[-5], valid_data[-6])
                    day_high = combine(valid_data[-7], valid_data[-8])
                    night_low = combine(valid_data[-9], valid_data[-10])
                    night_mod = combine(valid_data[-11], valid_data[-12])
                    night_high = combine(valid_data[-13], valid_data[-14])
                    
                    container_data = {
                        "isolation_distance": iso,
                        "day": {
                            "low_wind": day_low,
                            "moderate_wind": day_mod,
                            "high_wind": day_high
                        },
                        "night": {
                            "low_wind": night_low,
                            "moderate_wind": night_mod,
                            "high_wind": night_high
                        }
                    }
                    
                    final_output[current_id]["large_spill_details"][cont_type] = container_data
                    
                    data_buffer = [] 
                
                else:
                    pass
            
            else:
                if line.strip():
                     data_buffer.append(line)

        idx += 1

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=4)
    print(f"Table 3 processed: {len(final_output)} entries.")
    
    return processed_lines

if __name__ == "__main__":
    process_table_3("TIH_Table3.txt", "green_table_3.json")
