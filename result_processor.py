import requests
from datetime import datetime

class ResultProcessor:
    def __init__(self):
        pass
    
    def build_result(self, task_id, image_info, extraction_info, items, google_drive_url=None, file_name=None, mime_type=None):
        """構建結果字典"""
        return {
            'success': True,
            'message': 'Google Drive圖片下載和OCR處理成功',
            'task_id': task_id,
            'data': {
                'filename': image_info.get('unique_filename'),
                'original_filename': file_name or 'unknown',
                'google_drive_url': google_drive_url,
                'file_id': image_info.get('file_id'),
                'file_size': image_info.get('file_size'),
                'mime_type': mime_type or 'unknown',
                'upload_time': datetime.now().isoformat(),
                'image_info': {
                    'width': image_info.get('width'),
                    'height': image_info.get('height'),
                    'format': image_info.get('format')
                },
                'extracted_text': extraction_info.get('text'),
                'text_length': len(extraction_info.get('text', '')),
                'items': items
            }
        }
    
    def send_webhook(self, webhook_url, data):
        """發送webhook回調"""
        if not webhook_url:
            return None
            
        try:
            print(f"Sending callback to: {webhook_url}")
            response = requests.post(
                webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            result = {
                'sent': True,
                'status_code': response.status_code,
                'url': webhook_url
            }
            print(f"Callback sent successfully: {response.status_code}")
            return result
        except Exception as e:
            error_result = {
                'sent': False,
                'error': str(e),
                'url': webhook_url
            }
            print(f"Callback failed: {str(e)}")
            return error_result