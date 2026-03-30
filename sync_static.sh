#!/bin/bash
# 同步静态文件到 nginx 目录
# 在每次构建或更新容器后运行

CONTAINER_NAME="pmsmanagebot-app"
STATIC_DIR="/var/www/tgbot.misaya.org/static"

echo "同步静态文件..."

# 确保目录存在
mkdir -p "$STATIC_DIR"

# 从容器复制
docker cp "${CONTAINER_NAME}:/app/webapp-frontend/dist/." "$STATIC_DIR/"

# 设置权限
chown -R www-data:www-data "$STATIC_DIR"
chmod -R 755 "$STATIC_DIR"

echo "静态文件同步完成: $(ls -la $STATIC_DIR | wc -l) 个文件"
