
import re
import os

INPUT_FILE = "Prepared Data/ERG_Guides_Cleaned.txt"
OUTPUT_FILE = "Prepared Data/ERG_Guides_Cleaned.txt"

def fix_formatting():
    if not os.path.exists(INPUT_FILE):
        print(f"File not found: {INPUT_FILE}")
        return

    print(f"Reading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix 1: "Spill" should be on a new line
    # Matches ". Spill" at the end of a line (or line break in multiline string)
    # The string could be `. Spill` or `. Spill\r` or `. Spill\n`.
    # Using regex with MULTILINE flag to match `$` as end of line.
    
    # We replace ". Spill$" with ".\nSpill"
    # But content read includes newlines. So we can use simple replace or regex.
    # Be careful not to replace "Small Spill" or "Large Spill".
    # The grep showed specifically lines ending in ". Spill".
    
    new_content = re.sub(r'\. Spill$', '.\nSpill', content, flags=re.MULTILINE)
    
    # Fix 2: Remove "Oxidizing" from end of lines
    # Matches ". Oxidizing$"
    new_content = re.sub(r'\. Oxidizing$', '.', new_content, flags=re.MULTILINE)

    if content == new_content:
        print("No changes made.")
    else:
        print("Applying fixes...")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed content written to {OUTPUT_FILE}")

if __name__ == "__main__":
    fix_formatting()
