# Chemical Accident Emergency Response RAG System

這是一個基於 **緊急應變指南 (ERG, Emergency Response Guidebook)** 所建構的 RAG (Retrieval-Augmented Generation) 知識庫系統。

本系統旨在協助快速檢索化學事故中的關鍵應變資訊，包含：
- 化學品識別 (UN Number / Name)
- 潛在危害 (火災、健康危害)
- 公眾安全指引 (疏散距離、防護裝備)
- 緊急應變措施 (洩漏處理、急救)

## 📁 專案結構

- **`Prepared Data/`**: 已處理的結構化文字數據 (來源：ERG 指南)。
- **`build_rag_db.py`**: 建置向量資料庫 (ChromaDB) 的腳本。
- **`test_rag_system.py`**: 測試 RAG 系統檢索功能的腳本。
- **`erg_chroma_db/`**: (git ignored) 本地生成的向量資料庫，需透過腳本建立。
- **`extract_*.py`**: 各種 PDF 資料萃取工具 (供參考)。

## 🚀 快速開始 (Quick Start)

請按照以下步驟在您的環境中設置並執行此專案。

### 1. 環境設置

確保您已安裝 Python 3.10+。

```bash
# 建立虛擬環境
python3 -m venv venv

# 啟動虛擬環境 (Linux/Mac)
source venv/bin/activate

# 啟動虛擬環境 (Windows)
# venv\Scripts\activate

# 安裝依賴套件
pip install -r requirements.txt
```

### 2. 建置資料庫 (Build Database)

在執行任何檢索之前，必須先建立本地向量資料庫索引。這會讀取 `Prepared Data/` 中的檔案並存入 `erg_chroma_db/`。

```bash
python3 build_rag_db.py
```
*預計耗時：約 1-2 分鐘*

### 3. 執行測試 (Run Test)

執行測試腳本以驗證系統是否正常運作。此腳本會模擬查詢 **UN 1005 (Ammonia)** 並檢查是否能正確抓取到 **Table 3** 的詳細數據與 Guide 內容。

```bash
python3 test_rag_system.py
```

若看到 `SUCCESS` 與相關內容輸出，代表系統運作正常。

## 🔍 功能說明

本 RAG 系統包含兩個主要 Collection：
1. **`erg_materials`**: 
   - 透過化學品名稱或 UN 編號查詢。
   - 整合了 **Table 1 (TIH初始隔離)** 與 **Table 3 (大量洩漏詳細距離)** 的數據。
2. **`erg_guides`**: 
   - 儲存橘色頁面的應變指南。
   - 支援針對特定章節 (如 `POTENTIAL HAZARDS`) 的精確檢索。

---
**注意**：`erg_chroma_db` 資料夾已被設為忽略 (gitignore)，每次 clone 專案後請務必執行 `build_rag_db.py` 重建資料庫。
