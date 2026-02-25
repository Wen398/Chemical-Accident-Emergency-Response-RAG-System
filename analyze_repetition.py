import os
from collections import Counter

def analyze_repetition(file_path):
    print(f"Analyzing repetition in: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return

    # Filter out empty or whitespace-only lines
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    
    total_lines = len(non_empty_lines)
    unique_lines = set(non_empty_lines)
    unique_count = len(unique_lines)
    
    if total_lines == 0:
        print("File contains no non-empty lines.")
        return

    reduction = total_lines - unique_count
    reduction_percentage = (reduction / total_lines) * 100
    
    print("\n--- Repetition Analysis ---")
    print(f"Total non-empty lines: {total_lines}")
    print(f"Unique lines: {unique_count}")
    print(f"Reduction if unique only: {reduction} lines ({reduction_percentage:.2f}%)")
    
    # Analyze repetition frequency
    line_counts = Counter(non_empty_lines)
    most_common = line_counts.most_common(10)
    
    print("\n--- Most Repeated Lines (Top 10) ---")
    for line, count in most_common:
        # Truncate long lines for display
        display_line = (line[:75] + '...') if len(line) > 75 else line
        print(f"Count: {count:3d} | Line: {display_line}")

    # Basic analysis of line length to guess sentence vs paragraph
    avg_length = sum(len(line) for line in unique_lines) / unique_count
    print(f"\nAverage length of unique lines: {avg_length:.1f} characters")
    
    if avg_length > 100:
        print("Observation: High average line length suggests paragraph-level chunks.")
    elif avg_length < 50:
        print("Observation: Low average line length suggests sentence or phrase-level chunks.")
    else:
        print("Observation: Medium average line length.")

if __name__ == "__main__":
    file_path = 'Prepared Data/ERG_Guides_Cleaned.txt'
    analyze_repetition(file_path)
