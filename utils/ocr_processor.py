from google.cloud import vision
import cv2
import numpy as np

class OcrProcessor:
    def __init__(self):
        self.client = vision.ImageAnnotatorClient()
    
    def preprocess_image(self, image):
        """圖片預處理以提高OCR準確率"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    def extract_text(self, image_path):
        """使用 Google Cloud Vision OCR 從圖片中提取文字"""
        try:
            with open(image_path, "rb") as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = self.client.text_detection(image=image)
            texts = response.text_annotations
            if texts:
                return texts[0].description.strip()
            else:
                return ""
        except Exception as e:
            raise Exception(f"OCR識別失敗: {str(e)}")