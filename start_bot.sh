#!/bin/bash

echo "启动 PMSManageBot Bot 进程..."

cd /app/src

# 运行 Bot (包含 APScheduler 定时任务)
exec python3 -m app.main
