import os
import re
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
    # Convert to set for unique lines
    unique_lines_set = set(non_empty_lines)
    unique_lines_list = list(unique_lines_set)
    unique_count = len(unique_lines_set)
    
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
    most_common = line_counts.most_common(5)
    
    print("\n--- Most Repeated Lines (Top 5) ---")
    for line, count in most_common:
        display_line = (line[:75] + '...') if len(line) > 75 else line
        print(f"Count: {count} | Line: {display_line}")

    # Heuristic for sentence vs paragraph
    avg_length = sum(len(line) for line in unique_lines_list) / unique_count
    print(f"\nAverage length of unique lines: {avg_length:.1f} characters")
    
    # Check for multi-sentence lines
    multi_sentence_lines = 0
    # Simple heuristic: split by '. ', '? ', '! '
    sentence_splitter = re.compile(r'[.!?]\s+') 
    
    for line in unique_lines_list:
        parts = sentence_splitter.split(line)
        # remove empty strings
        parts = [p for p in parts if p.strip()]
        if len(parts) > 1:
            multi_sentence_lines += 1
            
    percent_multi = (multi_sentence_lines / unique_count) * 100
    print(f"Lines appearing to contain >1 sentence: {multi_sentence_lines} ({percent_multi:.1f}%)")
    
    if percent_multi > 30: 
         print("Conclusion: Significant portion of lines contain multiple sentences -> Paragraph level repetition is prevalent.")
    elif avg_length > 150:
         print("Conclusion: Lines are long -> Paragraph level repetition.") 
    else:
         print("Conclusion: Lines are short and mostly single sentences -> Sentence level repetition.")

if __name__ == "__main__":
    file_path = 'Prepared Data/ERG_Guides_Cleaned.txt'
    analyze_repetition(file_path)
