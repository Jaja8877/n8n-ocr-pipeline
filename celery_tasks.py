from celery_config import celery_app
from order_processor import OrderProcessor

# 全局實例
processor = OrderProcessor(
    order_csv_path="./客戶訂單資料.csv",
    upload_folder="uploads",
    max_file_size=20*1024*1024
)

@celery_app.task(bind=True, name='ocr_service.process_image')
def process_google_drive_image(self, google_drive_url, file_name=None, mime_type=None, webhook_url=None):
    """異步處理Google Drive圖片OCR任務"""
    try:
        
        # 整個流程都交給OrderProcessor處理
        result = processor.process(
            task_id=self.request.id,
            google_drive_url=google_drive_url,
            file_name=file_name,
            mime_type=mime_type,
            webhook_url=webhook_url
        )
        return result
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        # 更新任務狀態為失敗
        meta = {
            'exc_type': type(e).__name__,
            'exc_message': str(e)
        }
        if hasattr(self, 'task_progress'):
            meta.update(self.task_progress.__dict__)
        self.update_state(
            state='FAILURE',
            meta=meta
        )
        raise Exception(f"OCR處理錯誤: {str(e)}")