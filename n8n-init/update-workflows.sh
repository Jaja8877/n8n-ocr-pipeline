#!/bin/sh
# n8n-init/update-workflows.sh

echo "========= n8n-updater: Starting n8n initialization process... ========="

# 找到 n8n 容器的 ID
N8N_CONTAINER_ID=$(docker ps -qf "name=n8n-ocr-pipeline-n8n-1")

if [ -z "$N8N_CONTAINER_ID" ]; then
    echo "ERROR: Could not find the n8n container."
    exit 1
fi

echo "Found n8n container ID: $N8N_CONTAINER_ID"

# 等待 n8n 完全啟動
echo "Waiting for n8n to be fully ready..."
sleep 15

# 步骤 1: 安裝 curl 到 n8n 容器中
echo "Installing curl in n8n container..."
docker exec -u root "$N8N_CONTAINER_ID" apk add --no-cache curl

# 步骤 2: 修復 npm 權限問題
echo "Fixing npm permissions..."
docker exec -u root "$N8N_CONTAINER_ID" chown -R node:node /home/node/.npm || true

# 步骤 3: 使用 API 創建管理員用戶
echo "Creating admin user via API..."
RESPONSE=$(docker exec -u node "$N8N_CONTAINER_ID" sh -c "
curl -s -X POST http://localhost:5678/rest/owner/setup \
    -H 'Content-Type: application/json' \
    -d '{
        \"email\": \"${N8N_USER_EMAIL}\",
        \"firstName\": \"${N8N_USER_FIRSTNAME}\",
        \"lastName\": \"${N8N_USER_LASTNAME}\",
        \"password\": \"${N8N_USER_PASSWORD}\"
    }' \
    --max-time 30 \
    --retry 3
")

echo "API Response: $RESPONSE"

if echo "$RESPONSE" | grep -q "id"; then
    echo "✓ Admin user created successfully via API!"
elif echo "$RESPONSE" | grep -q "already"; then
    echo "⚠ User already exists"
else
    echo "⚠ User creation failed: $RESPONSE"
fi

# 步骤 4: 處理工作流文件並替換環境變數
echo "Processing workflow file and replacing environment variables..."
docker exec -u node "$N8N_CONTAINER_ID" sh -c "
cd /workflows

# 顯示環境變數
echo 'DEBUG: Environment variables:'
echo 'CONFIDENCE_LOW_ALERT_MAIL=${CONFIDENCE_LOW_ALERT_MAIL}'
echo 'GOOGLE_SHEET_URL=${GOOGLE_SHEET_URL}'

# 創建臨時處理過的工作流
cp My_workflow.json My_workflow_processed.json

# 使用更精確的 sed 替換
sed -i 's|\"{{ \$env\.CONFIDENCE_LOW_ALERT_MAIL }}\"|\"${CONFIDENCE_LOW_ALERT_MAIL}\"|g' My_workflow_processed.json
sed -i 's|\"{{ \$env\.GOOGLE_SHEET_URL }}\"|\"${GOOGLE_SHEET_URL}\"|g' My_workflow_processed.json

echo 'After replacement:'
grep -n 'sendTo\|value.*https' My_workflow_processed.json | head -5
"

# 步骤 5: 導入工作流（使用目錄）
echo "Importing workflows..."
docker exec -u node "$N8N_CONTAINER_ID" npx n8n import:workflow --separate --input=/workflows/

if [ $? -eq 0 ]; then
    echo "✓ Workflows imported successfully!"
else
    echo "⚠ Workflow import failed"
fi

# 步骤 6: 列出工作流
echo "Listing current workflows..."
docker exec -u node "$N8N_CONTAINER_ID" npx n8n list:workflow

# 步骤 7: 重啟 n8n 容器以啟用工作流
echo "Restarting n8n container to activate workflows..."
docker restart "$N8N_CONTAINER_ID"

echo "========= n8n-updater: Initialization process finished. ========="
echo "n8n is restarting... Please wait a moment then you can login with:"
echo "Email: ${N8N_USER_EMAIL}"
echo "Password: ${N8N_USER_PASSWORD}"
echo "URL: http://localhost:8080"