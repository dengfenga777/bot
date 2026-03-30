#!/bin/bash
# PMSManageBot 健康监控脚本
# 自动检测并修复网络连通性问题

LOG_FILE="/var/log/pmsmanagebot-monitor.log"
MAX_RETRIES=3
RETRY_DELAY=5

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

check_health() {
    curl -sf -m 5 http://localhost:5000/api/system/health > /dev/null 2>&1
    return $?
}

restart_container() {
    log "正在重启容器..."
    cd /opt/PMSManageBot
    docker compose -f docker-compose.prod.yaml restart app
    sleep 10
}

fix_network() {
    log "检测到网络问题，尝试修复..."
    
    # 方法1: 重启容器
    restart_container
    if check_health; then
        log "重启容器后恢复正常"
        return 0
    fi
    
    # 方法2: 重启Docker网络
    log "重启容器未解决，尝试重建网络..."
    cd /opt/PMSManageBot
    docker compose -f docker-compose.prod.yaml down
    docker network prune -f
    docker compose -f docker-compose.prod.yaml up -d
    sleep 15
    
    if check_health; then
        log "重建网络后恢复正常"
        return 0
    fi
    
    # 方法3: 重启Docker服务
    log "网络重建未解决，重启Docker服务..."
    systemctl restart docker
    sleep 10
    cd /opt/PMSManageBot
    docker compose -f docker-compose.prod.yaml up -d
    sleep 15
    
    if check_health; then
        log "重启Docker后恢复正常"
        return 0
    fi
    
    log "所有修复方法均失败，需要人工介入"
    return 1
}

# 主逻辑
retry_count=0
while [ $retry_count -lt $MAX_RETRIES ]; do
    if check_health; then
        exit 0
    fi
    retry_count=$((retry_count + 1))
    log "健康检查失败 (尝试 $retry_count/$MAX_RETRIES)"
    sleep $RETRY_DELAY
done

log "连续 $MAX_RETRIES 次健康检查失败，启动修复流程"
fix_network
