import json
import re

def process_table_2(txt_path, output_json_path):
    # Output structure: {id: [ {guide, name, gases}, ... ]}
    entries = {}
    
    # State for multiline
    current_entry_list = None # This will point to entries[id]
    current_entry_obj = None  # This will be the last object added
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    known_gases_tokens = {'HCl', 'HBr', 'HF', 'HI', 'HCN', 'H2S', 'NH3', 'NO2', 'PH3', 'SO2', 'Cl2', 'Br2', 'PH', 'H', 'SO', 'NH'} 
    
    # Set of gases that ARE permitted to accept a digit suffix from the next line
    permit_suffix_gases = {'PH', 'NH', 'SO', 'H', 'Br', 'Cl', 'I', 'F'}
    
    ignore_phrases = [
        "TABLE 2", "Materials Which Produce", "Water-Reactive Materials",
        "ID Guide", "Name of Material", "Page ",
        "Chemical Symbols", "Use this list only", 
        "(PIH in the US)", "Gas(es) When Spilled in Water", 
        "TIH Gas(es)", "No. No.", "Produced",
        "When Spilled in Water", "ELBAT"
    ]

    for line in lines:
        line_clean = line.strip()
        if not line_clean: continue
        
        # skip garbage lines that consist only of spaced out numbers like "2 2 3 2"
        if re.match(r'^[\d\s]+$', line_clean):
            continue

        # Skip Headers/Footers by phrase
        should_skip = False
        for phrase in ignore_phrases:
            if phrase in line_clean:
                should_skip = True
                break
        if should_skip: continue

        # Skip the Chemical Symbol Legend lines explicitly
        if "Hydrogen sulfide" in line_clean and "Bromine" in line_clean: continue
        if "Chlorine" in line_clean and "Hydrogen iodide" in line_clean: continue
        if "Fluorine" in line_clean and "Phosphine" in line_clean: continue
        if re.match(r'^\s*(?:Br|Cl|HBr|HCl|HCN|HF|HI|H2S|NH3|NO2|PH3|SO2)\s+', line_clean): continue

        parts = line_clean.split()
        
        # Check ID (Start of new entry)
        if re.match(r'^\d{4}$', parts[0]) and len(parts) >= 3 and re.match(r'^\d{3}$', parts[1]):
            un_id = parts[0]
            guide = parts[1]
            
            # Remaining parts are Name + Gas
            rest = parts[2:]
            
            # Extract Gas from End
            gases = []
            while rest and (rest[-1] in known_gases_tokens or re.match(r'^[A-Z][a-z]?\d?$', rest[-1])):
                gases.insert(0, rest.pop())
            
            material_name = " ".join(rest)
            
            new_obj = {
                "guide_no": guide,
                "material_name": material_name,
                "tih_gases": gases 
            }
            
            if un_id not in entries:
                entries[un_id] = []
            
            entries[un_id].append(new_obj)
            
            current_entry_list = entries[un_id]
            current_entry_obj = new_obj
            
        else:
            # Continuation Line
            if current_entry_obj is not None:
                content = line_clean
                
                is_gas_suffix = False
                last_gas = current_entry_obj['tih_gases'][-1] if current_entry_obj['tih_gases'] else ""
                
                if content.isdigit() and len(content) == 1:
                     if last_gas in permit_suffix_gases:
                         is_gas_suffix = True
                
                if is_gas_suffix:
                    current_entry_obj['tih_gases'][-1] += content
                else:
                    if line_clean in known_gases_tokens:
                        current_entry_obj['tih_gases'].append(line_clean)
                    else:
                        current_entry_obj['material_name'] += " " + line_clean
    
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)
    print(f"Table 2 processed: {len(entries)} IDs processed.")

if __name__ == "__main__":
    process_table_2("TIH_Table2.txt", "green_table_2.json")
