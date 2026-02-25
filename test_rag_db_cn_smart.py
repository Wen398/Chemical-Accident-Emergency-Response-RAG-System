import chromadb
from chromadb.utils import embedding_functions
import sys
import time
import os
import re
from typing import Optional, Dict, Any

# Configuration
DB_DIR = "erg_chroma_db_cn"

class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_step(msg):
    print(f"{Color.CYAN}➤ {msg}{Color.ENDC}")

def print_result(key, value):
    print(f"  {Color.GREEN}✔ {key}:{Color.ENDC} {value}")

def print_info(msg):
    print(f"  ℹ {msg}")

class ERG_RAG_Demo:
    def __init__(self):
        print(f"{Color.HEADER}[系統初始化] 正在連接至 ChromaDB 資料庫...{Color.ENDC}")
        
        if not os.path.exists(DB_DIR):
            print(f"{Color.FAIL}錯誤: 找不到資料庫目錄 '{DB_DIR}'。請先執行 build_rag_db_cn.py。{Color.ENDC}")
            sys.exit(1)
            
        # 使用與建立資料庫時相同的 Embedding 模型
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
        
        self.client = chromadb.PersistentClient(path=DB_DIR)
        try:
            self.collection = self.client.get_collection(name="erg_cn", embedding_function=ef)
            print(f"{Color.HEADER}資料庫連接成功。集合 'erg_cn' 包含 {self.collection.count()} 筆文件。\n{Color.ENDC}")
        except Exception as e:
            print(f"{Color.FAIL}載入集合時發生錯誤: {e}{Color.ENDC}")
            sys.exit(1)

    def search_material(self, query: str) -> Optional[Dict[str, Any]]:
        """
        示範如何搜尋物質：
        1. 優先檢查是否為 UN 編號
        2. 若非編號，則進行語意搜尋 + 關鍵字過濾
        """
        print_step(f"執行查詢: 搜尋物質 '{query}'")
        
        start_time = time.time()
        
        # 策略 1: 檢查查詢字串中是否包含 UN 編號 (例如 "UN 1017")
        un_id_match = re.search(r"(?:UN\s?|ID\s?)?(\d{4})\b", query, re.IGNORECASE)
        
        results = None
        match_method = "Unknown"
        
        if un_id_match and "Guide" not in query and "指南" not in query:
            un_id = un_id_match.group(1)
            match_method = "UN ID 精確匹配"
            results = self.collection.query(
                query_texts=[query],
                n_results=5,
                where={"$and": [{"un_id": un_id}, {"type": "material"}]}
            )
        else:
            # Semantic search
            results = self.collection.query(
                query_texts=[query],
                n_results=20, # Fetch more to filter
                where={"type": "material"}
            )
            
        elapsed = time.time() - start_time
        
        if not results or not results['ids'] or not results['ids'][0]:
            print(f"{Color.FAIL}  ✖ 未找到相關物質。{Color.ENDC}")
            return None

        candidates = []
        for i in range(len(results['ids'][0])):
            candidates.append({
                'meta': results['metadatas'][0][i],
                'dist': results['distances'][0][i] if results['distances'] else 0,
                'text': results['documents'][0][i]
            })

        best_match = None
        
        # Refinement Logic
        # If we didn't match by UN ID already
        if match_method != "UN ID 精確匹配":
            query_clean = query.replace("UN", "").replace("ID", "").strip().lower()
            
            # 1. Exact Name Match
            for cand in candidates:
                if cand['meta']['name'].strip().lower() == query_clean:
                    best_match = cand
                    match_method = f"精確名稱匹配 ('{cand['meta']['name']}')"
                    break
            
            # 2. Un ID match (if query was just a number but regex missed it somehow or mixed)
            if not best_match and query_clean.isdigit():
                 for cand in candidates:
                    if str(cand['meta']['un_id']) == query_clean:
                        best_match = cand
                        match_method = "UN ID 匹配"
                        break
            
            # 3. Contains Match (prioritize shorter/simpler names)
            if not best_match:
                 contains_cands = [c for c in candidates if query_clean in c['meta']['name'].lower()]
                 if contains_cands:
                     contains_cands.sort(key=lambda x: len(x['meta']['name']))
                     best_match = contains_cands[0]
                     match_method = f"部分名稱匹配 ('{best_match['meta']['name']}')"
            
            # 4. Fallback to vector similarity
            if not best_match:
                best_match = candidates[0]
                match_method = "向量語意相似度 (最相關結果)"
        else:
            best_match = candidates[0] # From UN ID query types

        meta = best_match['meta']
        
        print_info(f"匹配方式: {match_method}")
        print_result("識別物質", f"{meta['name']} (UN: {meta['un_id']})")
        print_result("參考指南", f"Guide {meta['guide_no']}")
        print_result("信心水準", f"高 (耗時 {elapsed:.4f}秒)")
        
        return meta

    def consult_guide(self, guide_no: str, specific_question: str):
        """
        示範如何檢索指南內容：
        根據指南編號 (Guide No) 檢索完整的應變指南文本。
        """
        
        # 處理指南編號格式 (例如去除 'P' 後綴)
        search_guide_no = guide_no
        if guide_no.endswith('P'):
            search_guide_no = guide_no.rstrip('P')
            print_info(f"注意: 將搜尋指南從 {guide_no} 調整為 {search_guide_no} (忽略 P 後綴)")
            
        print_step(f"執行查詢: 檢索指南 {search_guide_no} 的內容 (針對問題: {specific_question})")
        
        # 這裡是使用語意搜尋，同時限制 guide_no 以確保只搜尋該指南的範圍
        # 實務上，如果您只需要整篇指南，可以直接 filter guide_no 並取回所有 chunks

        
        results = self.collection.query(
            query_texts=[f"Guide {search_guide_no} {specific_question}"], 
            n_results=5, 
            where={"$and": [{"guide_no": search_guide_no}, {"type": "guide"}]}
        )
        
        if not results['ids'][0]:
            print(f"{Color.WARNING}  ⚠ 找不到指南內容。{Color.ENDC}")
            return

        doc_text = results['documents'][0][0]
        
        print_result("檢索結果", "成功獲取指南全文資料")
        print(f"\n{Color.BOLD}[指南 {search_guide_no} 內容預覽]{Color.ENDC}")
        print("------------------------------------------------")
        
        # 僅顯示前 1000 個字元作為示範
        print(doc_text[:1000] + "...\n(下略)\n")
        
        print("------------------------------------------------\n")
        

    def run_scenario(self, title: str, material_query: str, guide_query: Optional[str] = None):
        print(f"{Color.BOLD}{Color.UNDERLINE}測試案例: {title}{Color.ENDC}")
        print("------------------------------------------------")
        
        # 1. 搜尋並識別物質
        material_data = self.search_material(material_query)
        if not material_data:
            print("\n")
            return

        # 2. 檢查 Metadata 中的關鍵危害 (TIH, 禁水, 聚合)
        print_info("檢查物質 Metadata 中的危害標記...")
        has_hazard = False
        
        # 從 Metadata 讀取 TIH 資訊
        if material_data.get('is_tih', False):
            has_hazard = True
            print(f"  {Color.WARNING}⚠ 吸入性中毒危害 (TIH) 物質{Color.ENDC}")
            
            # Safe access to fields (they might be empty strings)
            # Metadata keys in build_rag_db_cn.py were: small_iso, small_day, etc.
            small_iso = material_data.get('small_iso', 'N/A') or 'N/A'
            small_day = material_data.get('small_day', 'N/A') or 'N/A'
            small_night = material_data.get('small_night', 'N/A') or 'N/A'

            large_iso = material_data.get('large_iso', 'N/A') or 'N/A'
            large_day = material_data.get('large_day', 'N/A') or 'N/A'
            large_night = material_data.get('large_night', 'N/A') or 'N/A'
            large_note = material_data.get('large_note', '')
            
            print(f"    {Color.BOLD}小量洩漏 (Small Spill):{Color.ENDC}")
            print(f"      - 隔離距離: {small_iso}")
            print(f"      - 防護距離 (日間): {small_day}")
            print(f"      - 防護距離 (夜間): {small_night}")
            
            print(f"    {Color.BOLD}大量洩漏 (Large Spill):{Color.ENDC}")
            if large_note:
                print(f"      - 注意: {large_note}")
            else:
                print(f"      - 隔離距離: {large_iso}")
                print(f"      - 防護距離 (日間): {large_day}")
                print(f"      - 防護距離 (夜間): {large_night}")
        
        if material_data.get('is_water_reactive', False):
             has_hazard = True
             print(f"  {Color.WARNING}⚠ 禁水性 (遇水反應) 物質{Color.ENDC}")
             gases = material_data.get('water_reactive_gases', '未知氣體')
             if gases:
                 print(f"    遇水產生氣體: {gases}")

        if material_data.get('is_polymerization', False):
             has_hazard = True
             print(f"  {Color.WARNING}⚠ 聚合反應危害{Color.ENDC}")

        if not has_hazard:
            print(f"  {Color.GREEN}✔ 未發現特殊危害標記 (非 TIH/禁水/聚合反應物質){Color.ENDC}")

        # 3. Guide Consultation (if needed)
        if guide_query:
            self.consult_guide(str(material_data['guide_no']), guide_query)
        else:
            print_info("此案例不包含指南內容檢索。")
        
        print("\n")

def main():
    # 初始化測試類別
    tester = ERG_RAG_Demo()
    
    # --- 測試案例 1 ---
    tester.run_scenario(
        title="1. 一般查詢 (標準物質)",
        material_query="Gasoline", 
        guide_query="發生火災時應該使用什麼滅火劑？"
    )

    # --- 測試案例 2 ---
    tester.run_scenario(
        title="2. TIH 物質查詢 (吸入性危害 & 隔離距離)",
        material_query="Chlorine (氯)", 
        guide_query="吸入時的急救措施為何？"
    )

    # --- 測試案例 3 ---
    tester.run_scenario(
        title="3. 禁水性物質查詢 (Metadata 檢查)",
        material_query="三氯矽烷", # Trichlorosilane
        guide_query="我可以用大量水滅火嗎？"
    )
    
    # --- 測試案例 4 ---
    tester.run_scenario(
        title="4. UN 編號查詢",
        material_query="UN 1005",
        guide_query="防護距離是多少？"
    )

    # --- 測試案例 5 (口語化提問測試) ---
    tester.run_scenario(
        title="5. 口語化提問測試 (誤食)",
        material_query="Arsenic",
        guide_query="如果不小心喝到了怎麼辦？"
    )
    
    # --- 測試案例 6 (口語化提問測試 - 疏散) ---
    tester.run_scenario(
        title="6. 口語化提問測試 (疏散距離)",
        material_query="UN 1017",
        guide_query="附近的居民需要撤離多遠？"
    )

if __name__ == "__main__":
    main()
