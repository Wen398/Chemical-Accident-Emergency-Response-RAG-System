import fitz

def convert_pdf_to_text(pdf_path, txt_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # 取得純文字
        text = page.get_text("text")
        
        full_text += text
        
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    
    doc.close()
    print(f"轉換完成！文字檔已儲存至: {txt_path}")

# 執行轉換
convert_pdf_to_text("TIH_Table1.pdf", "TIH_Table1.txt")