#!/bin/bash
# PMSManageBot 健康检查和自动修复脚本
# 建议通过 cron 每 5 分钟运行一次

LOG_FILE="/var/log/pmsmanagebot_health.log"
ALERT_FILE="/tmp/pmsmanagebot_alert_sent"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

send_alert() {
    # 避免重复告警（1小时内只发一次）
    if [ -f "$ALERT_FILE" ]; then
        ALERT_AGE=$((($(date +%s) - $(stat -c %Y $ALERT_FILE 2>/dev/null || echo 0))))
        if [ $ALERT_AGE -lt 3600 ]; then
            return
        fi
    fi
    
    log "发送告警: $1"
    # 这里可以添加通知逻辑（如发送到 Telegram）
    touch $ALERT_FILE
}

clear_alert() {
    rm -f $ALERT_FILE
}

check_container() {
    local container=$1
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        return 1
    fi
    return 0
}

check_api() {
    local response
    response=$(curl -sf --max-time 10 http://127.0.0.1:5000/health 2>/dev/null)
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    if echo "$response" | grep -q '"status":"ok"'; then
        return 0
    fi
    return 1
}

check_redis() {
    docker exec pmsmanagebot-app python3 -c "
import redis
r = redis.Redis(host='redis', port=6379)
r.ping()
" 2>/dev/null
    return $?
}

check_tautulli() {
    docker exec pmsmanagebot-app python3 -c "
import urllib.request
urllib.request.urlopen('http://tautulli:8181/api/v2?cmd=status&apikey=bf6df6413ebb4f63a0e5f414db6a6851', timeout=10)
" 2>/dev/null
    return $?
}

fix_networks() {
    log "修复网络连接..."
    
    # 连接到必要的网络
    docker network connect pmsmanagebot_pmsmanagebot_net pmsmanagebot-app 2>/dev/null
    docker network connect tautulli_default pmsmanagebot-app 2>/dev/null
    
    log "网络修复完成"
}

# 主检查逻辑
main() {
    ISSUES=0
    
    # 检查 App 容器
    if ! check_container "pmsmanagebot-app"; then
        log "错误: pmsmanagebot-app 容器未运行"
        ISSUES=1
        
        # 尝试启动
        log "尝试启动服务..."
        cd /opt/PMSManageBot && docker compose -f docker-compose.prod.yaml up -d
        sleep 30
    fi
    
    # 检查 Redis 容器
    if ! check_container "pmsmanagebot-redis"; then
        log "错误: pmsmanagebot-redis 容器未运行"
        ISSUES=1
    fi
    
    # 检查 API
    if ! check_api; then
        log "警告: API 健康检查失败"
        ISSUES=1
        
        # 检查是否是网络问题
        if ! check_redis; then
            log "Redis 连接失败，尝试修复网络..."
            fix_networks
            sleep 5
        fi
    fi
    
    # 检查 Redis 连接
    if ! check_redis; then
        log "警告: Redis 连接失败"
        fix_networks
        ISSUES=1
    fi
    
    # 检查 Tautulli 连接
    if ! check_tautulli; then
        log "警告: Tautulli 连接失败"
        fix_networks
        ISSUES=1
    fi
    
    # 处理结果
    if [ $ISSUES -eq 0 ]; then
        clear_alert
        log "健康检查通过"
    else
        send_alert "PMSManageBot 健康检查发现问题，已尝试自动修复"
    fi
    
    return $ISSUES
}

main
