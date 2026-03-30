#!/bin/bash
# 确保 pmsmanagebot-app 连接到必要的网络

echo "[$(date)] 检查并修复网络连接..."

# 连接到 Redis 网络
if ! docker network inspect pmsmanagebot_default | grep -q pmsmanagebot-app; then
    docker network connect pmsmanagebot_default pmsmanagebot-app 2>/dev/null &&         echo "已连接到 pmsmanagebot_default 网络" ||         echo "pmsmanagebot_default 网络连接失败或已连接"
fi

# 连接到 Tautulli 网络
if ! docker network inspect tautulli_default | grep -q pmsmanagebot-app; then
    docker network connect tautulli_default pmsmanagebot-app 2>/dev/null &&         echo "已连接到 tautulli_default 网络" ||         echo "tautulli_default 网络连接失败或已连接"
fi

echo "[$(date)] 网络检查完成"
