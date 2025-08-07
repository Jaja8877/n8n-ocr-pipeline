# OCR N8N 自動化處理流水線

## 此專案僅供 Stark 面試審核使用

本專案是基於 n8n 自動化的發票 OCR 處理流水線，具備 Google Drive 整合、OCR 處理和自動資料輸入至 Google Sheets 功能。

## 功能特色

- 📄 **OCR 處理**: 使用 Google Vision API 自動從圖片中提取文字
- 🔗 **N8N 整合**: 完整的工作流程自動化，支援 webhook
- 📊 **Google Sheets**: 自動資料輸入和追蹤
- 🤖 **AI 匹配**: 使用 Gemini AI 進行產品資料庫的模糊匹配
- 📧 **郵件提醒**: 低信心度評分通知
- 🐳 **Docker 支援**: 完整容器化部署
- 🌐 **Ngrok 整合**: 提供公開 webhook 端點用於測試

## 環境需求

在設置此專案之前，請確保您已安裝：

- [Docker](https://www.docker.com/get-started) 和 [Docker Compose](https://docs.docker.com/compose/install/)
- Python 3.9+ (用於本地開發)
- Git 版本控制工具

## 必要帳號申請

### 1. Google Cloud Platform (GCP)
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 啟用以下 API：
   - Google Vision API
   - Google Drive API  
   - Google Sheets API
4. 建立服務帳戶：
   - 前往 IAM 和管理 → 服務帳戶
   - 點擊「建立服務帳戶」
   - 下載 JSON 金鑰檔案
   - 將檔案重新命名為 `your-gcp-key.json` 並放置於專案根目錄

### 2. Ngrok 帳號
1. 在 [ngrok.com](https://ngrok.com/) 註冊帳號
2. 從儀表板取得您的 authtoken
3. 取得免費版靜態網址URL
![Alt text](readme-pics/ngrok-setup.png)

### 3. Google Gemini AI
1. 訪問 [Google AI Studio](https://aistudio.google.com/)
2. 建立 API 金鑰
3. 儲存 API 金鑰用於環境設定

### 4. Gmail 帳號
1. 使用現有的 Gmail 帳號或建立新帳號
2. 用於 N8N Gmail 整合，您需要設定 OAuth2 憑證：
   - 前往 [Google Cloud Console](https://console.cloud.google.com/)
   - API 和服務 → 憑證
   - 為網頁應用程式建立 OAuth 2.0 用戶端 ID
   - 為 N8N 新增授權的重新導向 URI

### 5. Google Sheets
1. 建立新的 Google 試算表用於資料儲存
2. 將試算表與您的 GCP 服務帳戶電子郵件共用
3. 複製試算表 URL 用於環境設定

## 安裝與設定

### 1. 複製專案
```bash
git clone <repository-url>
cd stark-interview
```

### 2. 啟動DOCKER
```bash
docker-compose up --build -d
```
