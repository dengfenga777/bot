#!/bin/bash

# 设置默认值
WEBAPP_URL=${WEBAPP_URL:-"http://localhost:6000"}
WORKERS=${WORKERS:-4}

# 替换前端构建文件中的 API URL
if [ -d "/app/webapp-frontend/dist" ]; then
    echo "正在更新前端 API URL 为: $WEBAPP_URL"
    find /app/webapp-frontend/dist -name "*.js" -exec sed -i "s|http://localhost:6000|$WEBAPP_URL|g" {} +
    echo "前端配置更新完成"
fi

# 获取 CPU 核心数
if [ "$WORKERS" = "auto" ]; then
    WORKERS=$(nproc)
    if [ "$WORKERS" -gt 8 ]; then
        WORKERS=8
    fi
fi

echo "启动应用 (Workers: $WORKERS)..."

# 使用 gunicorn + uvicorn workers
# 注意：正确的模块路径是 app.webapp:app
exec gunicorn "app.webapp:app" \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers $WORKERS \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --graceful-timeout 10 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
