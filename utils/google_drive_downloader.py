import re
import requests
from io import BytesIO
from PIL import Image
from pdf2image import convert_from_bytes  # 確保已安裝 pdf2image 和 poppler

class GoogleDriveDownloader:
    def __init__(self, max_file_size=20 * 1024 * 1024):
        self.max_file_size = max_file_size
    
    def extract_file_id(self, url):
        """從Google Drive URL中提取文件ID"""
        patterns = [
            r'/file/d/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
            r'/d/([a-zA-Z0-9-_]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def download(self, google_drive_url):
        """下載Google Drive文件，如果是PDF則轉換為圖片，返回圖片數據和格式"""
        file_id = self.extract_file_id(google_drive_url)
        if not file_id:
            raise ValueError('無效的Google Drive URL')
        
        # 構建下載URL
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # 下載文件
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()
        
        # 檢查文件大小
        file_data = response.content
        if len(file_data) > self.max_file_size:
            raise ValueError(f'文件大小超過{self.max_file_size/1024/1024}MB限制')
        
        # 判斷文件類型
        try:
            image = Image.open(BytesIO(file_data))
            image.verify()
            image = Image.open(BytesIO(file_data))
            file_extension = image.format.lower() if image.format else 'png'
            image_data = file_data  # 保存原始圖片數據
            file_type = "image"
        except Exception:
            file_type = "pdf"

        if file_type == "image":
            image = Image.open(BytesIO(file_data))
            image.verify()
            image = Image.open(BytesIO(file_data))
            file_extension = image.format.lower() if image.format else 'png'
            image_data = file_data
        elif file_type == "pdf":
            try:
                images = convert_from_bytes(file_data)
                if not images:
                    raise ValueError('PDF轉換為圖片失敗')
                
                # 使用第一頁作為圖片
                image = images[0]
                file_extension = 'png'
                
                # 將圖片保存到內存中
                image_buffer = BytesIO()
                image.save(image_buffer, format='PNG')
                image_data = image_buffer.getvalue()
                
            except Exception as e:
                raise ValueError(f'文件不是有效的圖片或PDF格式: {e}')
        else:
            raise ValueError(f'文件不是有效的圖片或PDF格式')
            
        return {
            'file_id': file_id,
            'image_data': image_data,
            'image': image,
            'file_extension': file_extension,
            'file_size': len(image_data),
            'width': image.width,
            'height': image.height,
            'format': image.format
        }