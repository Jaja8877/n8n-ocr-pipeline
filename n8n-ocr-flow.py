from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from celery_tasks import process_google_drive_image
from datetime import datetime
import re
import requests

app = Flask(__name__)
CORS(app)

# 簡單的 HTML 表單模板
# 修改 FORM_TEMPLATE 的這部分
FORM_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OCR 結果修正</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .item { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        input, select { margin: 5px; padding: 8px; width: 200px; }
        button { padding: 10px 20px; background: #007cba; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #005a87; }
        .score-low { background-color: #ffe6e6; }
        .score-medium { background-color: #fff3e0; }
        .score-high { background-color: #e8f5e8; }
    </style>
</head>
<body>
    <h1>OCR 結果修正</h1>
    <p><strong>檔案:</strong> {{ data['original_filename'] }}</p>
    <p><strong>任務ID:</strong> {{ task_id }}</p>
    
    <form id="correctionForm">
        <input type="hidden" name="task_id" value="{{ task_id }}">
        <input type="hidden" name="webhook_url" value="{{ webhook_url }}">
        
        {% for item in data['items'] if item['match_score'] < 0.7 %}
        <div class="item {% if item['match_score'] < 0.6 %}score-low{% elif item['match_score'] < 0.8 %}score-medium{% else %}score-high{% endif %}">
            <h3>項目 {{ loop.index }}</h3>
            <p><strong>原始輸入:</strong> {{ item['original_input'] }}</p>
            <p><strong>匹配信心度:</strong> {{ item['match_score'] }}</p>
            
            <label>產品ID:</label>
            <input type="text" name="items[{{ loop.index0 }}][product_id]" value="{{ item['product_id'] }}">
            
            <label>匹配名稱:</label>
            <input type="text" name="items[{{ loop.index0 }}][matched_name]" value="{{ item['matched_name'] }}">
            
            <label>商品名稱:</label>
            <input type="text" name="items[{{ loop.index0 }}][item_name]" value="{{ item['item_name'] }}">
            
            <label>數量:</label>
            <input type="number" name="items[{{ loop.index0 }}][quantity]" value="{{ item['quantity'] }}" step="0.1">
            
            <input type="hidden" name="items[{{ loop.index0 }}][original_input]" value="{{ item['original_input'] }}">
        </div>
        {% endfor %}
        
        <button type="submit">提交修正</button>
    </form>

    <script>
        document.getElementById('correctionForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {
                task_id: formData.get('task_id'),
                webhook_url: formData.get('webhook_url'),
                items: []
            };
            
            // 解析表單數據
            let itemIndex = 0;
            while (formData.get(`items[${itemIndex}][product_id]`) !== null) {
                // 獲取所有項目，不論信心指數
                data.items.push({
                    product_id: formData.get(`items[${itemIndex}][product_id]`),
                    matched_name: formData.get(`items[${itemIndex}][matched_name]`),
                    item_name: formData.get(`items[${itemIndex}][item_name]`),
                    quantity: parseFloat(formData.get(`items[${itemIndex}][quantity]`)),
                    original_input: formData.get(`items[${itemIndex}][original_input]`),
                    match_score: "已人工修正"
                });
                itemIndex++;
            }
            
            // 發送修正後的數據
            fetch('/submit-correction', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('修正提交成功！');
                    window.close();
                } else {
                    alert('提交失敗: ' + data.error);
                }
            })
            .catch(error => {
                alert('提交錯誤: ' + error);
            });
        });
    </script>
</body>
</html>
"""

class RequestProcessor:
    """處理請求數據的輔助類"""
    
    @staticmethod
    def extract_google_drive_data(data):
        """從請求數據中提取Google Drive相關信息"""
        google_drive_url = None
        file_name = None
        mime_type = None
        webhook_url = data.get('webhookUrl')
        
        if 'google_drive_url' in data:
            google_drive_url = data['google_drive_url']
            file_name = data.get('fileName')
            mime_type = data.get('mimeType')
            
        elif '請上傳欲辨識圖片_urls' in data:
            urls_data = data['請上傳欲辨識圖片_urls']
            if isinstance(urls_data, dict) and 'url' in urls_data:
                google_drive_url = urls_data['url']
                file_name = urls_data.get('fileName')
                mime_type = urls_data.get('mimeType')
        
        return google_drive_url, file_name, mime_type, webhook_url
    
    @staticmethod
    def parse_request_data(request):
        """解析請求數據"""
        if request.content_type and 'application/json' in request.content_type:
            return request.get_json()
        elif request.form:
            return request.form.to_dict()
        else:
            try:
                return request.get_json(force=True)
            except:
                raise ValueError('無效的請求格式')

class ResponseBuilder:
    """構建響應的輔助類"""
    
    @staticmethod
    def success_response(message, task_id, status_code=202):
        """構建成功響應"""
        return jsonify({
            'success': True,
            'message': message,
            'task_id': task_id,
            'status_url': f'/status/{task_id}'
        }), status_code
    
    @staticmethod
    def error_response(error_message, status_code=400):
        """構建錯誤響應"""
        return jsonify({
            'success': False,
            'error': error_message
        }), status_code
    
    @staticmethod
    def task_status_response(task):
        """構建任務狀態響應"""
        if task.state == 'PENDING':
            response = {
                'state': 'PENDING',
                'status': '任務正在等待處理...'
            }
        elif task.state == 'PROGRESS':
            response = {
                'state': 'PROGRESS',
                'step': task.info.get('step', ''),
                'progress': task.info.get('progress', 0)
            }
        elif task.state == 'SUCCESS':
            response = {
                'state': 'SUCCESS',
                'result': task.result
            }
        else:
            # 任務失敗
            response = {
                'state': task.state,
                'error': str(task.info)
            }
        return jsonify(response), 200

@app.route('/upload', methods=['POST'])
def upload_image():
    """接收請求並啟動異步OCR任務"""
    try:
        # 解析請求數據
        data = RequestProcessor.parse_request_data(request)
        
        # 提取Google Drive URL和相關信息
        google_drive_url, file_name, mime_type, webhook_url = RequestProcessor.extract_google_drive_data(data)
        
        if not google_drive_url:
            return ResponseBuilder.error_response('請提供Google Drive文件URL', 400)
        
        # 啟動異步任務
        task = process_google_drive_image.delay(
            google_drive_url=google_drive_url,
            file_name=file_name,
            mime_type=mime_type,
            webhook_url=webhook_url
        )
        
        return ResponseBuilder.success_response('任務已提交，正在處理中', task.id)
        
    except ValueError as e:
        return ResponseBuilder.error_response(str(e), 400)
    except Exception as e:
        return ResponseBuilder.error_response(f'服務器錯誤: {str(e)}', 500)

@app.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """查詢任務狀態"""
    try:
        task = process_google_drive_image.AsyncResult(task_id)
        return ResponseBuilder.task_status_response(task)
        
    except Exception as e:
        return ResponseBuilder.error_response(f'查詢任務狀態失敗: {str(e)}', 500)

@app.route('/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'OCR Image Upload Service with Celery'
    }), 200

@app.route('/correction-form/<task_id>')
def correction_form(task_id):
    """顯示人工修正表單"""
    try:
        # 從 Celery 取得任務結果
        task = process_google_drive_image.AsyncResult(task_id)
        print(f"DEBUG: Task ID: {task_id}")
        print(f"DEBUG: Task State: {task.state}")
        
        # 如果任務還沒完成，等待它完成
        if task.state != 'SUCCESS':
            if task.state == 'PENDING':
                return render_template_string("""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>任務處理中</title>
                        <meta http-equiv="refresh" content="5">
                        <style>
                            body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
                            .loader { border: 5px solid #f3f3f3; border-radius: 50%; border-top: 5px solid #3498db; width: 30px; height: 30px; animation: spin 2s linear infinite; margin: 20px auto; }
                            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                        </style>
                    </head>
                    <body>
                        <h1>任務處理中</h1>
                        <div class="loader"></div>
                        <p>任務 {{ task_id }} 正在處理中，請稍候...</p>
                        <p>頁面將每 5 秒自動刷新</p>
                    </body>
                    </html>
                """, task_id=task_id)
            else:
                return ResponseBuilder.error_response(f'任務狀態異常: {task.state}', 400)
        
        result = task.result
        webhook_url = request.args.get('webhook_url', '')
        
        # 調試輸出
        print(f"DEBUG: Result type: {type(result)}")
        print(f"DEBUG: Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        # 確保 result 有正確的資料結構
        if not result or not isinstance(result, dict) or 'data' not in result:
            return ResponseBuilder.error_response('任務結果格式錯誤', 500)
        
        data = result['data']
        print(f"DEBUG: Data type: {type(data)}")
        print(f"DEBUG: Data keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
        
        # 確保 data 有 items 鍵，且其值是一個列表
        if not isinstance(data, dict) or 'items' not in data or not isinstance(data['items'], list):
            # 如果 data 中沒有 items 鍵或其值不是列表，創建一個空列表
            if isinstance(data, dict):
                data['items'] = []
                print("DEBUG: Created empty items list")
            else:
                return ResponseBuilder.error_response('數據格式錯誤：data 不是字典', 500)
        
        return render_template_string(
            FORM_TEMPLATE, 
            data=data, 
            task_id=task_id,
            webhook_url=webhook_url
        )
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error in correction_form: {str(e)}")
        print(traceback.format_exc())
        return ResponseBuilder.error_response(f'載入表單失敗: {str(e)}', 500)

@app.route('/submit-correction', methods=['POST'])
def submit_correction():
    """處理修正後的數據並回傳給 n8n"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        webhook_url = data.get('webhook_url')
        corrected_items = data.get('items', [])  # 確保獲取到 items
        
        if not webhook_url:
            return ResponseBuilder.error_response('缺少 webhook URL', 400)
        
        print(f"DEBUG: Received correction for task {task_id}")
        print(f"DEBUG: Webhook URL: {webhook_url}")
        print(f"DEBUG: Corrected items: {corrected_items}")  # 打印確認
        
        # 構建修正後的回應
        corrected_result = {
            'data': {  # 將所有數據包裝在 data 字段下
                'success': True,
                'message': '人工修正完成',
                'task_id': task_id,
                'corrected': True,
                'items': corrected_items,
                'correction_timestamp': datetime.now().isoformat()
            }
        }
        
        # 發送回 n8n
        try:
            response = requests.post(
                webhook_url,
                json=corrected_result,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response body: {response.text}")
            
            if response.status_code == 200:
                return jsonify({'success': True, 'message': '修正數據已提交'})
            elif response.status_code == 409:
                return jsonify({
                    'success': True, 
                    'message': '修正數據已提交（webhook 已被使用過，但修正已成功完成）'
                })
            else:
                return ResponseBuilder.error_response(f'回傳失敗: {response.status_code}, 響應內容: {response.text}', 500)
                
        except Exception as e:
            print(f"DEBUG: Request exception: {str(e)}")
            return ResponseBuilder.error_response(f'發送請求失敗: {str(e)}', 500)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error in submit_correction: {str(e)}")
        print(traceback.format_exc())
        return ResponseBuilder.error_response(f'提交修正失敗: {str(e)}', 500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)