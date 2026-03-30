# PMSManageBot 运维文档

## 问题根因分析

### 问题1: Docker 网络隔离
**现象**: Redis/Tautulli 连接失败，主机名无法解析
**原因**: 容器手动启动时未指定网络，导致各容器在不同网络中隔离
- pmsmanagebot-app: bridge 网络
- pmsmanagebot-redis: pmsmanagebot_default 网络  
- tautulli: tautulli_default 网络

**解决方案**: 使用 docker-compose.prod.yaml 统一管理网络
- app 和 redis 共享 pmsmanagebot_net 网络
- app 连接到 tautulli_default 外部网络

### 问题2: 流量统计定时任务未运行
**现象**: 流量数据为 0，无新数据写入
**原因**: Bot 进程（含 scheduler）未启动，只运行了 webapp
- main.py 中的 scheduler 需要 bot 进程运行
- webapp 容器只启动了 gunicorn

**解决方案**: 
- 添加 cron 定时任务每 6 小时运行流量统计更新
- update_traffic.sh 脚本通过 docker exec 执行更新

### 问题3: 环境变量格式错误
**现象**: 容器启动失败，pydantic 验证错误
**原因**: 列表类型环境变量格式不正确
- 错误: TG_ADMIN_CHAT_ID=647050755,7012408492
- 正确: TG_ADMIN_CHAT_ID=["647050755","7012408492"]

**解决方案**: .env 文件中列表类型使用 JSON 数组格式

### 问题4: nginx 504/499 超时
**现象**: 外部请求大量超时
**原因**: 
- 单进程 uvicorn 无法处理并发
- 静态文件经过后端处理
- 无连接池复用

**解决方案**:
- gunicorn + 4 uvicorn workers 处理并发
- nginx 直接服务静态文件
- upstream keepalive 32 连接池

---

## 目录结构

```
/opt/PMSManageBot/
├── docker-compose.prod.yaml  # Docker Compose 配置
├── data/
│   ├── .env                  # 环境变量配置
│   └── data.db               # SQLite 数据库
├── manage.sh                 # 管理脚本
├── health_check.sh           # 健康检查脚本
├── update_traffic.sh         # 流量统计更新脚本
├── sync_static.sh            # 静态文件同步脚本
├── start.sh                  # 容器启动脚本
└── MAINTENANCE.md            # 本文档
```

---

## 常用命令

### 服务管理
```bash
# 启动服务
/opt/PMSManageBot/manage.sh start

# 停止服务
/opt/PMSManageBot/manage.sh stop

# 重启服务
/opt/PMSManageBot/manage.sh restart

# 查看状态
/opt/PMSManageBot/manage.sh status

# 查看日志
/opt/PMSManageBot/manage.sh logs

# 健康检查
/opt/PMSManageBot/manage.sh health

# 更新部署
/opt/PMSManageBot/manage.sh update
```

### 手动操作
```bash
# 手动更新流量统计
/opt/PMSManageBot/update_traffic.sh

# 手动健康检查
/opt/PMSManageBot/health_check.sh

# 同步静态文件
/opt/PMSManageBot/sync_static.sh
```

### systemctl 服务
```bash
# 启用开机自启
systemctl enable pmsmanagebot

# 手动启动
systemctl start pmsmanagebot

# 查看状态
systemctl status pmsmanagebot
```

---

## 定时任务 (Cron)

| 时间 | 任务 | 说明 |
|------|------|------|
| */5 * * * * | health_check.sh | 健康检查，自动修复 |
| 0 */6 * * * | update_traffic.sh | 流量统计更新 |
| 0 3 * * * | 日志清理 | 删除 7 天前的日志 |
| 0 4 * * 0 | sync_static.sh | 每周同步静态文件 |

---

## 日志文件

| 文件 | 说明 |
|------|------|
| /var/log/pmsmanagebot_health.log | 健康检查日志 |
| /var/log/pmsmanagebot_traffic.log | 流量统计更新日志 |
| /var/log/pmsmanagebot_sync.log | 静态文件同步日志 |

---

## 故障排查

### 容器无法启动
```bash
# 查看日志
docker logs pmsmanagebot-app

# 常见原因:
# 1. 模块路径错误 - 检查 start.sh 使用 app.webapp:app
# 2. 环境变量格式 - 检查 .env 列表使用 JSON 格式
# 3. 依赖服务 - 确保 redis 先启动
```

### 网络连接失败
```bash
# 检查网络
docker network ls
docker inspect pmsmanagebot-app --format '{{json .NetworkSettings.Networks}}'

# 手动连接网络
docker network connect tautulli_default pmsmanagebot-app
```

### 流量统计为 0
```bash
# 检查数据库
docker exec pmsmanagebot-app python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/data.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM line_traffic_stats')
print('总记录:', cur.fetchone()[0])
"

# 手动触发更新
/opt/PMSManageBot/update_traffic.sh
```

---

## 更新日期
2026-01-09
