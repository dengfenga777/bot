#!/bin/bash
# PMSManageBot 管理脚本
# 用法: ./manage.sh [start|stop|restart|status|logs|health|update]

set -e
cd /opt/PMSManageBot

COMPOSE_FILE="docker-compose.prod.yaml"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

start() {
    log "启动 PMSManageBot 服务..."
    docker compose -f $COMPOSE_FILE up -d
    
    # 等待服务启动
    log "等待服务就绪..."
    sleep 10
    
    # 验证网络连接
    log "验证网络连接..."
    docker exec pmsmanagebot-app python3 -c "
import socket
try:
    print('Redis:', socket.gethostbyname('redis'))
except: print('Redis: 连接失败')
try:
    print('Tautulli:', socket.gethostbyname('tautulli'))
except: print('Tautulli: 连接失败')
"
    
    # 同步静态文件
    if [ -x "./sync_static.sh" ]; then
        log "同步静态文件..."
        ./sync_static.sh
    fi
    
    log "服务启动完成"
    health
}

stop() {
    log "停止 PMSManageBot 服务..."
    docker compose -f $COMPOSE_FILE down
    log "服务已停止"
}

restart() {
    log "重启 PMSManageBot 服务..."
    stop
    sleep 3
    start
}

status() {
    log "服务状态:"
    docker compose -f $COMPOSE_FILE ps
}

logs() {
    docker compose -f $COMPOSE_FILE logs -f --tail=100
}

health() {
    log "健康检查:"
    
    # 检查容器状态
    echo "=== 容器状态 ==="
    docker compose -f $COMPOSE_FILE ps
    
    # 检查 API 健康
    echo ""
    echo "=== API 健康检查 ==="
    curl -s http://127.0.0.1:5000/health | python3 -m json.tool 2>/dev/null || echo "API 不可用"
    
    # 检查系统健康
    echo ""
    echo "=== 系统组件健康 ==="
    curl -s http://127.0.0.1:5000/api/system/health | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('状态:', d.get('status'))
    for name, info in d.get('components', {}).items():
        print(f'  {name}: {info.get("status")}')
except: print('无法获取健康状态')
"
}

update() {
    log "更新 PMSManageBot..."
    
    # 拉取最新代码
    git pull origin main 2>/dev/null || log "Git pull 跳过"
    
    # 重新构建镜像
    log "构建新镜像..."
    docker build --no-cache -t pmsmanagebot:latest .
    
    # 重启服务
    restart
    
    log "更新完成"
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    logs)    logs ;;
    health)  health ;;
    update)  update ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs|health|update}"
        exit 1
        ;;
esac
