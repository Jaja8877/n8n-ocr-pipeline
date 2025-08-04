import os
from dotenv import load_dotenv
import pandas as pd
import re
import google.generativeai as genai
import json

load_dotenv()  # 讀取 .env

def extract_chinese_name(text):
    match = re.match(r'^([\u4e00-\u9fff]+)', text)
    if match:
        return match.group(1)
    return text
class OrderFuzzyMatcher:
    def __init__(self, path, model="gemini-2.0-flash"):
        self.path = path
        self.items = self._load_items()
        self.item_names = self.items['品名'].tolist()
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=gemini_api_key)
        self.model = model

    def _load_items(self):
        try:
            items = pd.read_csv(self.path, dtype=str, encoding="big5")
        except UnicodeDecodeError:
            import chardet
            with open(self.path, "rb") as f:
                result = chardet.detect(f.read())
                encoding = result["encoding"]
            items = pd.read_csv(self.path, dtype=str, encoding=encoding)
        return items

    def fuzzy_match_items(self, query, top_k=1):
        query = extract_chinese_name(query)
        prompt = (
            f"請根據語意，從下列商品品名清單中找出最接近「{query}」的品名，"
            "只回傳一個最接近的結果，格式為：\n"
            "{\"matched_name\": 品名, \"score\": 分數}\n"
            f"品名清單：{self.item_names}"
        )
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(prompt)
        content = response.text
        print("LLM 回傳內容：", content)
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            json_str = content[start:end+1]
            try:
                result = json.loads(json_str)
            except Exception:
                result = {}
        else:
            result = {}
        return result

# 使用範例
if __name__ == "__main__":
    matcher = OrderFuzzyMatcher("./客戶訂單資料.csv")
    print(matcher.items.head())
    result = matcher.fuzzy_match_items("東坡肉12x1242瑰")
    print(result)