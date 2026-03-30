# PMSManageBot

Plex / Emby 用户管理 Telegram 机器人，带 WebApp 面板、积分系统、签到排行、勋章系统和多种运营功能。

当前仓库已经整理为适合直接上传 GitHub 的项目版本，服务器运行数据、备份文件、缓存文件和构建产物已从仓库中移除，不会把线上环境里的私有数据一起带上来。

## 功能概览

- Plex / Emby 用户注册、绑定、资料同步
- Telegram Bot 交互与 WebApp 面板
- 积分系统、邀请系统、Premium 解锁
- 多种排行榜与签到玩法
- 勋章系统与排行榜加成
- Redis 缓存与定时任务
- Docker Compose 生产部署

## 签到与勋章说明

项目内包含签到排行榜与勋章系统，当前规则包括：

- 签到总榜前三专属勋章
- 第 1 名加成 `1.5`
- 第 2 名加成 `1.3`
- 第 3 名加成 `1.1`
- 同签到天数时，先完成该签到次数的用户排名更靠前

相关勋章会出现在各个榜单展示中，但不会出现在普通勋章商店中。

## 技术栈

- Python 3.11
- `python-telegram-bot`
- FastAPI + Uvicorn / Gunicorn
- Redis
- SQLAlchemy
- Vue 3 + Vuetify
- Docker Compose

## 目录结构

```text
PMSManageBot/
├── .env.example                  # 配置模板
├── Dockerfile
├── docker-compose.prod.yaml      # 生产环境编排
├── src/app/                      # 后端源码
├── tests/                        # 测试
├── webapp-frontend/              # WebApp 前端
├── scripts/                      # 维护/迁移脚本
├── nginx_configs/                # Nginx / 路由相关配置
├── MAINTENANCE.md                # 维护说明
└── data/                         # 运行时数据目录（本地保留空目录，不提交私有数据）
```

## 快速开始

### 1. 准备配置文件

```bash
mkdir -p data
cp .env.example data/.env
```

然后按你的环境修改 `data/.env`。

### 2. 构建前端

如果你需要重新构建 WebApp 静态资源：

```bash
cd webapp-frontend
npm install
npm run build
cd ..
```

默认情况下，后端会从 `webapp-frontend/dist` 提供前端静态文件。

### 3. 使用 Docker Compose 启动

```bash
docker compose -f docker-compose.prod.yaml up -d --build
```

默认会启动以下服务：

- `redis`
- `bot`
- `app`

### 4. 查看运行状态

```bash
docker compose -f docker-compose.prod.yaml ps
docker compose -f docker-compose.prod.yaml logs -f app
docker compose -f docker-compose.prod.yaml logs -f bot
```

## 配置说明

主要配置都在 `data/.env` 中，仓库内只保留 `.env.example` 模板。常用配置包括：

- Telegram Bot Token 与管理群信息
- Plex / Emby 地址与管理员凭据
- WebApp 监听地址与访问域名
- Redis 地址
- 积分、邀请、Premium、流量额度配置
- 路由线路与高级线路配置

请不要把真实的 `data/.env` 提交到 GitHub。

## 生产部署注意事项

- `docker-compose.prod.yaml` 里包含一个外部网络 `tautulli_default`
- 如果你的环境没有这个网络，需要先创建，或者自行修改 compose 文件
- `app` 容器通过 Gunicorn 启动 FastAPI WebApp
- `bot` 容器负责 Telegram Bot 与定时任务
- 前端静态资源可以通过项目自身提供，也可以配合 Nginx 做静态分发

如果你使用 Nginx 托管静态文件，更新前端或勋章资源后，记得同步静态目录。

## 本地开发

后端代码位于 `src/app`，前端代码位于 `webapp-frontend`。

常见开发动作：

```bash
# 后端依赖
uv sync

# 前端开发
cd webapp-frontend
npm install
npm run serve
```

测试目录在 `tests`。

## 维护脚本

仓库中保留了一些用于迁移、同步和运维的脚本，位于 `scripts` 和项目根目录，例如：

- 用户信息同步
- 线路数据迁移
- Plex / Emby 数据修复
- 静态资源同步
- 健康检查

使用前建议先阅读脚本内容，确认是否适合你的环境。

## 致谢

感谢 [WithdewHua](https://github.com/WithdewHua) 提供的原始项目与思路参考。
