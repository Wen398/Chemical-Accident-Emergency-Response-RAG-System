import pdfplumber
import json
import re

def reverse_word(text):
    # Reverse string and swap parentheses for individual words
    rev = text[::-1]
    return rev.translate(str.maketrans("()", ")("))

def parse_data_string(data_str):
    # data_str should be like "30 m (100 ft) 0.1 km (0.1 mi)..."
    items = []
    
    # Regex for "Refer to Table 3"
    ref_table_pattern = re.compile(r'Refer\s+to\s+Table\s+3', re.IGNORECASE)
    
    # Regex for distance
    # Matches: 30 m (100 ft)
    dist_pattern = re.compile(r'\d+(?:\.\d+)?\s*(?:m|km)\s*\(\d+(?:\.\d+)?\s*(?:ft|mi)\)')
    
    cursor = 0
    length = len(data_str)
    
    while cursor < length:
        match_dist = dist_pattern.match(data_str[cursor:])
        if match_dist:
            items.append(match_dist.group(0))
            cursor += len(match_dist.group(0))
            while cursor < length and data_str[cursor].isspace():
                cursor += 1
            continue
            
        match_ref = ref_table_pattern.match(data_str[cursor:])
        if match_ref:
            items.append("Refer to Table 3")
            cursor += len(match_ref.group(0))
            while cursor < length and data_str[cursor].isspace():
                cursor += 1
            continue
            
        cursor += 1
        
    return items

def extract_green_table_1(pdf_path, output_json_path):
    results = {}
    print(f"Start processing: {pdf_path}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            processed_count = 0
            
            for i, page in enumerate(pdf.pages):
                words = page.extract_words()
                if not words: continue

                # Group words by X-axis (Cluster Tolerance ~ 4.0)
                words.sort(key=lambda w: w['x0'])
                clusters = []
                current_cluster = []
                current_x_sum = 0
                
                for w in words:
                    if not current_cluster:
                        current_cluster.append(w)
                        current_x_sum = w['x0']
                        continue
                    
                    avg_x = current_x_sum / len(current_cluster)
                    if abs(w['x0'] - avg_x) < 4.0:
                        current_cluster.append(w)
                        current_x_sum += w['x0']
                    else:
                        clusters.append(current_cluster)
                        current_cluster = [w]
                        current_x_sum = w['x0']
                if current_cluster: clusters.append(current_cluster)
                
                for idx, cl in enumerate(clusters):
                    # Check for ID (Digits 4, Top > 500)
                    id_words = [w for w in cl if w['text'].isdigit() and len(w['text'])==4 and w['top'] > 500]
                    if not id_words: continue
                    
                    # Sort Cluster by Top Descending (High Top -> Low Top)
                    # This reconstructs the vertical text flow Top-to-Bottom
                    cl_sorted = sorted(cl, key=lambda w: w['top'], reverse=True)
                    
                    # Find ID
                    id_word = next((w for w in cl_sorted if w['text'].isdigit() and len(w['text'])==4 and w['top'] > 500), None)
                    if not id_word: continue
                    
                    un_id = reverse_word(id_word['text'])
                    
                    # Guide (Top 470-500)
                    guide_words = [w for w in cl_sorted if 470 < w['top'] < 500 and (w['text'].isdigit() or 'P' in w['text'])]
                    guide_parts = [reverse_word(w['text']) for w in guide_words]
                    guide_no = " ".join(guide_parts)
                    
                    # Name (Top 380-470)
                    name_words = [w for w in cl_sorted if 380 <= w['top'] <= 470 and w not in guide_words and w != id_word]
                    material_name = " ".join([reverse_word(w['text']) for w in name_words]).strip()
                    
                    # Data (Top < 380)
                    data_words = [w for w in cl_sorted if w['top'] < 380]
                    
                    # Check neighbors if data is missing or looks incomplete
                    has_units = any(w['text'] in ['m', 'km', 'ft', 'mi', '3'] for w in data_words)
                    
                    if not has_units:
                         # Try Next
                        if idx + 1 < len(clusters):
                            next_cl = clusters[idx+1]
                            next_has_id = any(w['text'].isdigit() and len(w['text'])==4 and w['top'] > 500 for w in next_cl)
                            if not next_has_id:
                                next_sorted = sorted(next_cl, key=lambda w: w['top'], reverse=True)
                                data_words.extend([w for w in next_sorted if w['top'] < 380])
                        
                        # Try Prev
                        if idx - 1 >= 0:
                            prev_cl = clusters[idx-1]
                            prev_has_id = any(w['text'].isdigit() and len(w['text'])==4 and w['top'] > 500 for w in prev_cl)
                            if not prev_has_id:
                                prev_sorted = sorted(prev_cl, key=lambda w: w['top'], reverse=True)
                                data_words.extend([w for w in prev_sorted if w['top'] < 380])
                        
                        # Sort combined data words again by Top Descending
                        data_words.sort(key=lambda w: w['top'], reverse=True)

                    data_str = " ".join([reverse_word(w['text']) for w in data_words])
                    
                    data_items = parse_data_string(data_str)
                    
                    entry = {
                        "guide_no": guide_no,
                        "material_name": material_name,
                        "small_spill": {},
                        "large_spill": {},
                        "source": "ERG_2024_Table1"
                    }
                    
                    if len(data_items) >= 1: entry["small_spill"]["isolation_distance"] = data_items[0]
                    if len(data_items) >= 2: entry["small_spill"]["protect_day"] = data_items[1]
                    if len(data_items) >= 3: entry["small_spill"]["protect_night"] = data_items[2]
                    
                    if len(data_items) >= 4: 
                        if data_items[3] == "Refer to Table 3":
                             entry["large_spill"]["note"] = "Refer to Table 3"
                        else:
                             entry["large_spill"]["isolation_distance"] = data_items[3]
                    
                    if len(data_items) >= 5: entry["large_spill"]["protect_day"] = data_items[4]
                    if len(data_items) >= 6: entry["large_spill"]["protect_night"] = data_items[5]

                    results[un_id] = entry
                    processed_count += 1
                
                if (i + 1) % 5 == 0:
                    print(f"Processed {i+1}/{total_pages} pages...")
                    
    except Exception as e:
        print(f"Error: {e}")

    print(f"Total extracted: {len(results)}")
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"Saved to {output_json_path}")

if __name__ == "__main__":
    extract_green_table_1("TIH_Table1.pdf", "green_table_1.json")
