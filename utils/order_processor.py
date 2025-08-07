from .google_drive_downloader import GoogleDriveDownloader
from .file_manager import FileManager
from .ocr_processor import OcrProcessor
from .fuzzy_matching import OrderFuzzyMatcher
from .result_processor import ResultProcessor
import re

class OrderProcessor:
    def __init__(self, order_csv_path="./客戶訂單資料.csv", upload_folder="uploads", max_file_size=20*1024*1024):
        self.downloader = GoogleDriveDownloader(max_file_size=max_file_size)
        self.file_manager = FileManager(upload_folder=upload_folder)
        self.ocr_processor = OcrProcessor()
        self.fuzzy_matcher = OrderFuzzyMatcher(order_csv_path)
        self.result_processor = ResultProcessor()
    
    def extract_item_and_quantity(self, item_text):
        """從項目文字中提取商品名稱和數量"""
        # 移除多餘空白
        item_text = item_text.strip()
        if not item_text:
            return "", 1
        
        # 常見數量模式：數字+單位，或純數字
        quantity_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:斤|公斤|kg|包|盒|袋|瓶|罐|個|顆|片|條|支|根|張|份|組|套|束|把)',
            r'(\d+(?:\.\d+)?)$',  # 純數字在結尾
            r'(\d+(?:\.\d+)?)\s*(?:x|X|\*)',  # 數字+乘號
        ]
        
        quantity = 1
        item_name = item_text
        
        for pattern in quantity_patterns:
            match = re.search(pattern, item_text)
            if match:
                quantity = float(match.group(1))
                # 移除數量部分，保留商品名稱
                item_name = re.sub(pattern, '', item_text).strip()
                break
        
        return item_name, quantity

    def process(self, task_id, google_drive_url, file_name=None, mime_type=None, webhook_url=None):
        """處理完整的OCR工作流"""
        try:
            # 1. 下載圖片
            download_info = self.downloader.download(google_drive_url)
            
            # 2. 保存圖片
            file_path, unique_filename = self.file_manager.save_image(
                download_info['image_data'], 
                download_info['file_extension']
            )
            
            # 3. OCR識別
            extracted_text = self.ocr_processor.extract_text(file_path)
            
            # 4. 提取行項目並模糊匹配
            extracted_items = extracted_text.split('\n') if extracted_text else []
            items = []
            
            for item in extracted_items:
                print("Processing item:", item)
                
                # 提取商品名稱和數量
                item_name, quantity = self.extract_item_and_quantity(item)
                
                if not item_name:  # 跳過空的項目
                    continue
                    
                matches = self.fuzzy_matcher.fuzzy_match_items(item_name)
                print("Processing matches:", matches)
                
                if isinstance(matches, dict) and matches.get("matched_name"):
                    best_match = matches
                    # 用 matched_name 找出對應 row
                    product_row = self.fuzzy_matcher.items[self.fuzzy_matcher.items['品名'] == best_match["matched_name"]]
                    product_id = product_row['品號'].values[0] if not product_row.empty and '品號' in product_row.columns else ""
                    
                    items.append({
                        "product_id": product_id,
                        "matched_name": best_match["matched_name"],
                        "original_input": item,
                        "item_name": item_name,  # 處理後的商品名稱
                        "quantity": quantity,     # 提取的數量
                        "match_score": float(best_match["score"]) if best_match.get("score") is not None else 0
                    })
            
            # 5. 構建結果
            image_info = {
                'unique_filename': unique_filename,
                'file_id': download_info['file_id'],
                'file_size': download_info['file_size'],
                'width': download_info['width'],
                'height': download_info['height'],
                'format': download_info['format']
            }
            
            extraction_info = {
                'text': extracted_text
            }
            
            result = self.result_processor.build_result(
                task_id=task_id,
                image_info=image_info,
                extraction_info=extraction_info,
                items=items,
                google_drive_url=google_drive_url,
                file_name=file_name,
                mime_type=mime_type
            )
            
            # 6. 清理臨時文件
            self.file_manager.cleanup(file_path)
            
            # 7. Webhook回調
            if webhook_url:
                callback_status = self.result_processor.send_webhook(webhook_url, result)
                result['callback_status'] = callback_status
            
            return result
            
        except Exception as e:
            # 錯誤處理和回調
            if webhook_url:
                self.result_processor.send_webhook(
                    webhook_url,
                    {
                        'success': False,
                        'error': str(e),
                        'task_id': task_id
                    }
                )
            raise Exception(f"處理失敗: {str(e)}")