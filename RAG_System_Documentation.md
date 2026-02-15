# RAG System Documentation: Chemical Accident System

## 1. Overview
This RAG (Retrieval-Augmented Generation) system is designed to provide rapid access to critical safety information from the **Emergency Response Guidebook (ERG)**. It allows an AI assistant to retrieve accurate emergency response protocols based on material names or UN numbers.

## 2. Updated Data Sources (Prepared Data)
The system ingests data from the following prepared files:
- **`ERG_Guides_Cleaned.txt`** (Orange Section): Contains the core safety guides (Potential Hazards, Public Safety, Emergency Response).
- **`ERG_Index_Processed.txt`** (Yellow/Blue Sections): Maps UN IDs and Material Names to Guide Numbers.
- **`green_table_1.json`**: Initial Isolation and Protective Action Distances for TIH (Toxic Inhalation Hazard) materials.
- **`green_table_2.json`**: List of Water-Reactive materials which produce Toxic Gases.
- **`green_table_3.json`**: **(New)** Detailed Large Spill isolation distances for 6 common TIH gases (e.g., Ammonia, Chlorine), broken down by container type and wind speed.

## 3. Database Structure
The system uses **ChromaDB** as the vector database, organized into two collections:

### Collection A: `erg_materials`
Stores information about specific chemical materials.
- **Document Text**: The original index entry + **Appended Green Table 3 Data** (if applicable).
- **Metadata**:
  - `un_id`: UN Number (e.g., "1005")
  - `name`: Material Name (e.g., "Ammonia, anhydrous")
  - `guide_no`: Reference to the Orange Guide
  - `is_tih`: Boolean (True if Toxic Inhalation Hazard)
  - `is_water_reactive`: Boolean
  - `small_iso`, `small_day`, `small_night`: Small spill distances (from Table 1)
  - `large_iso`, `large_day`, `large_night`: Large spill distances (from Table 1)
  - `large_note`: Notes like "Refer to Table 3"
  - `table3_content`: Text representation of the detailed Table 3 data.

### Collection B: `erg_guides`
Stores the text of the emergency response guides.
- **Document Text**: The guide content divided into sections (Potential Hazards, Public Safety, Emergency Response).
- **Metadata**:
  - `guide_no`: The Guide Number (e.g., "125")
  - `section`: The specific section name.

## 4. Key Improvements
- **Table 3 Integration**: For materials like Ammonia (UN 1005) and Chlorine (UN 1017), the system now automatically appends the detailed "Table 3" data (Container Types, Wind Speeds) into the material's searchable text. This ensures the RAG model "sees" this critical data immediately.
- **Metadata Filtering**: Queries can filter by `un_id` or `guide_no` for precise retrieval.

## 5. Testing
A test script `test_rag_system.py` is included to verify the integrity of the data.
- It searches for **UN 1005 (Ammonia)**.
- It verifies that the **Table 3 data** is successfully attached to the record.
- It retrieves the corresponding **Guide 125**.

## 6. Usage
To query the system:
1. **Identify Material**: Search `erg_materials` using the chemical name or UN number.
2. **Check Context**: Read the retrieved document to see if TIH data (Table 1 or Table 3) is present.
3. **Get Guide**: Use the `guide_no` from the material record to query `erg_guides` for specific response actions.
