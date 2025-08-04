import os
import uuid

class FileManager:
    def __init__(self, upload_folder='uploads'):
        self.upload_folder = upload_folder
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def save_image(self, image_data, file_extension):
        """保存圖片到臨時文件並返回路徑"""
        unique_filename = f"{str(uuid.uuid4())}.{file_extension}"
        file_path = os.path.join(self.upload_folder, unique_filename)
        
        with open(file_path, 'wb') as f:
            f.write(image_data)
            
        return file_path, unique_filename
    
    def cleanup(self, file_path):
        """清理臨時文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            print(f"清理臨時文件失敗: {e}")
            return False