# 化學災害緊急應變 RAG 系統 (Chemical Emergency Response RAG System)

這是一個基於 **緊急應變指南 (ERG, Emergency Response Guidebook)** 建構的 RAG (Retrieval-Augmented Generation) 知識庫系統（繁體中文版）。

本系統旨在協助快速檢索化學事故中的關鍵應變資訊，包含：
- **化學品識別**：透過 UN 編號 (如 "UN 1017") 或化學品中文/英文名稱進行模糊搜尋。
- **潛在危害資訊**：火災或爆炸風險、健康危害說明。
- **公眾安全指引**：包含 **TIH (吸入性中毒危害)** 物質的初始隔離距離與防護距離（Table 1 & Table 3 數據整合）。
- **緊急應變措施**：針對不同災情（火災、洩漏、急救）提供具體的指南建議。

## 📁 專案結構

本專案主要包含以下核心檔案與資料夾：

- **`demo_rag_cn.py`**：主要的演示腳本。執行此腳本可進行自動化測試與互動式查詢演示。
- **`build_rag_db_cn.py`**：建置向量資料庫 (ChromaDB) 的工具。
- **`Prepared Data_CN/`**：經過清洗與結構化的中文 ERG 數據資料夾。
    - `ERG_Guides_Cleaned_CN.txt`：完整的指南文本。
    - `ERG_Index_Processed_CN.txt`：化學品索引與關聯數據。
    - `green_table_*.json`：綠色頁面 (TIH/Reactives) 的結構化數據。
- **`erg_chroma_db_cn/`**：(自動生成) 本地向量資料庫儲存目錄。

---

## 🚀 快速開始 (Quick Start)

請按照以下步驟在您的本機環境中設置並執行此專案。

### 1. 環境設置 (Installation)

本專案建議使用 Python 3.10 或更高版本。

```bash
# 1. Clone 專案後，建議建立虛擬環境
python3 -m venv venv

# 2. 啟動虛擬環境 (Linux/Mac)
source venv/bin/activate
# (Windows 使用: venv\Scripts\activate)

# 3. 安裝依賴套件
pip install -r requirements.txt
```

### 2. 建置資料庫 (Build Database)

在進行查詢之前，必須先將文字數據向量化並存入本地資料庫。這會讀取 `Prepared Data_CN/` 中的檔案。

```bash
python3 build_rag_db_cn.py
```
> **注意**：初次執行時會自動下載 embedding 模型 (`paraphrase-multilingual-MiniLM-L12-v2`)，可能需耗時 1-3 分鐘。看到 "RAG Build Complete!" 即表示完成。

### 3. 執行演示與測試 (Run Demo)

我們提供了一個演示腳本，展示系統的多種查詢能力，包含基礎搜尋、TIH 距離計算以及自然語言整合查詢。

```bash
python3 demo_rag_cn.py
```

執行後，您將看到系統自動演示以下情境：
1. **標準物質查詢** (如：汽油) -> 顯示危害與指南。
2. **TIH 物質查詢** (如：氯氣) -> 自動列出日間/夜間的疏散距離。
3. **禁水性物質查詢** -> 顯示遇水反應風險。
4. **口語化提問** (如："誤食砷怎麼辦？") -> 系統理解並檢索急救資訊。
5. **整合式查詢演示** -> 模擬使用者輸入一句話，系統自動識別物質並回答應變措施。

---

## 🔍 功能特色

### 1. 混合式搜尋 (Hybrid Search)
系統結合了 **關鍵字匹配 (UN ID)** 與 **語意向量搜尋 (Semantic Search)**。
- 輸入 `UN 1017` 或 `UN1017` 可精確定位物質。
- 輸入 `Chlorine` 或 `氯氣` 甚至描述性語句，也能透過向量相似度找到對應物質。

### 2. 智慧資料整合 (Smart Data Enrichment)
在檢索化學品時，系統會自動從 ERG 的綠色頁面 (Green Pages) 提取關鍵數據並合併顯示，無需翻閱多份文件：
- **Table 1**：小量/大量洩漏的初始隔離距離。
- **Table 2**：遇水產生有毒氣體的資訊。
- **Table 3**：針對特定六種吸入性毒害氣體 (如氨、氯) 的大量洩漏詳細防護距離。

### 3. 文檔檢索 (Retrieval Augmented Generation ready)
系統能根據用戶問題 (如「發生火災怎麼辦？」)，精準檢索對應指南 (Guide) 中的相關段落 (如 `FIRE OR EXPLOSION` 章節)，為串接 LLM 生成回答提供高品質的 context。

---

## 📝 常見問題與疑難排解 (Troubleshooting)

- **Q: 搜尋 "Chlorine" 時出現 "Chlorobenzyl chlorides"？**
  - **A**: 這是向量搜尋的正常特性。當輸入較短的單字時，模型可能會匹配到包含該單字的長字串。建議優先使用 **UN 編號 (UN 1017)** 進行最精確的查詢，或在查詢中加入更多描述 (如 "Chlorine gas")。

- **Q: 執行時顯示 `ModuleNotFoundError`？**
  - **A**: 請確認您已啟動虛擬環境 (`source venv/bin/activate`) 並且已執行 `pip install -r requirements.txt`。

- **Q: 是否需要 OpenAI API Key？**
  - **A**: 不需要。本系統目前使用開源的 `sentence-transformers` 模型在本地端運作，完全免費且離線可用。

