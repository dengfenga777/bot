#!/bin/bash
# 更新流量统计数据

echo "[$(date)] 开始更新流量统计..."

docker exec pmsmanagebot-app python3 -c "
import asyncio
import sys
sys.path.insert(0, '/app/src')

async def run():
    from app.update_db import update_traffic_stats_from_tautulli
    await update_traffic_stats_from_tautulli()

asyncio.run(run())
" 2>&1

echo "[$(date)] 流量统计更新完成"
