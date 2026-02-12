import fitz  # PyMuPDF

def split_pdf(input_path, output_path, start_page, end_page):
    """
    擷取指定範圍的頁面並存成新的 PDF
    注意：PyMuPDF 的頁碼是從 0 開始計算
    """
    doc = fitz.open(input_path)
    new_doc = fitz.open()
    
    # 擷取範圍 (例如 10-50 頁，程式碼寫 9 到 50)
    new_doc.insert_pdf(doc, from_page=start_page-1, to_page=end_page-1)
    
    new_doc.save(output_path)
    new_doc.close()
    doc.close()
    print(f"成功儲存指定頁面至: {output_path}")

# 使用範例
# split_pdf("ERG2024-Eng-Web-a.pdf", "ERG_Material_Yellow_Section.pdf",  30, 89)
# split_pdf("ERG2024-Eng-Web-a.pdf", "ERG_Material_Blue_Section.pdf", 90, 149)
# split_pdf("ERG2024-Eng-Web-a.pdf", "ERG_Guide_Section.pdf", 150, 281)
split_pdf("ERG2024-Eng-Web-a.pdf", "TIH_Table3.pdf",  343, 345)