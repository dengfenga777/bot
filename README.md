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

现在 `docker-compose.prod.yaml` 已经补上 `build: .`，后续执行 `up -d --build` 时会真正重建 `pmsmanagebot:latest`，不会再出现“容器重启了但镜像还是旧代码”的情况。

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
- 当前仓库的 `Dockerfile` 会把前端构建产物一起打进镜像，常规更新不需要再手动同步 Nginx 静态目录

如果你的服务器没有 `tautulli_default` 网络，可以先执行：

```bash
docker network create tautulli_default
```

## 共享线路部署

如果你要启用“用户自定义反代域名 / 共享线路切换”，推荐使用仓库里新增的 `OpenResty` 媒体网关方案，而不是直接改宿主机 Nginx 模块。

原因很简单：

- 标准 Nginx 默认没有 Lua 模块
- 共享线路的动态路由依赖 Lua 读取 Redis
- 宿主机保留现有 Nginx 负责证书和 443，风险最低

### 推荐架构

```text
Cloudflare / 用户请求
        |
        v
宿主机 Nginx :443
        |
        +--> OpenResty 官方入口 :18080 / :18081
        |         |
        |         +--> 本地 Plex / Emby
        |         |
        |         +--> Redis 中记录的用户线路
        |         |
        |         +--> 用户自定义共享反代域名
        |
        +--> OpenResty origin 验签入口 :18082 / :18083
                  |
                  +--> 本地 Plex / Emby（仅允许验签通过的回源请求）
```

### 仓库内新增内容

- `docker-compose.media-gateway.yaml`：媒体网关容器编排
- `openresty/`：OpenResty 镜像与 Lua 路由脚本
- `nginx_configs/host_proxy/`：宿主机标准 Nginx 前置配置样板

### 媒体网关启动方式

```bash
docker compose -f docker-compose.media-gateway.yaml build
docker compose -f docker-compose.media-gateway.yaml up -d
```

默认约定如下：

- OpenResty 监听宿主机 `127.0.0.1:18080` 处理 Plex
- OpenResty 监听宿主机 `127.0.0.1:18081` 处理 Emby
- OpenResty 监听宿主机 `127.0.0.1:18082` 处理 Plex origin 回源
- OpenResty 监听宿主机 `127.0.0.1:18083` 处理 Emby origin 回源
- Redis 走 `127.0.0.1:6379`
- 本地 Plex 默认入口是 `http://127.0.0.1:32400`
- 本地 Emby 默认入口是 `http://127.0.0.1:8096`

如有需要可以在 `docker-compose.media-gateway.yaml` 中自行调整。

### 宿主机 Nginx 需要做什么

把 Plex / Emby 的宿主机站点配置替换为：

- `nginx_configs/host_proxy/plex.misaya.org.conf`
- `nginx_configs/host_proxy/emby.misaya.org.conf`
- `nginx_configs/host_proxy/plex-origin.misaya.org.conf`
- `nginx_configs/host_proxy/emby-origin.misaya.org.conf`

其中：

- `plex.misaya.org` / `emby.misaya.org` 继续作为客户端公开入口
- `plex-origin.misaya.org` / `emby-origin.misaya.org` 只作为共享线路最终回源
- origin 入口会校验官方媒体网关附带的验签头，未通过直接返回 `403`

### 关键环境要求

- `data/.env` 中要有可用的 `PLEX_API_TOKEN`
- 建议在 `data/.env` 中设置独立的 `MEDIA_ROUTE_SIGNING_SECRET`
- Redis 必须能从宿主机 `127.0.0.1:6379` 访问
- 用户自定义共享反代域名必须已经完成 HTTPS 反代并且能从服务器侧连通
- 用户填写的共享域名不能直接填写 `plex-origin.misaya.org` / `emby-origin.misaya.org`

### 单域名用户反代怎么接

用户在 miniapp 里填写的应该是自己的统一域名，例如 `media.user.com`，不是官方入口，也不是 origin 域名。

仓库里提供了可直接改名套用的样板：

- `nginx_configs/user_proxy/media.user.com.conf.example`

推荐让用户自己的 Nginx 根据官方入口附带的 `X-PMS-Entry-Host` 来分流到对应的 origin 域名，并原样透传以下头：

- `X-PMS-Entry-Host`
- `X-PMS-Route-Service`
- `X-PMS-Route-Timestamp`
- `X-PMS-Route-Signature`

这套模式下：

- 客户端仍然只访问 `plex.misaya.org` / `emby.misaya.org`
- 官方入口识别用户线路后，把请求转发到用户自己的域名
- 用户自己的域名再把请求回源到 `plex-origin.misaya.org` / `emby-origin.misaya.org`
- origin 域名没有合法签名时不会直接放行，因此不能当成公开入口使用

### 回滚方式

如果要回滚，只需要：

1. 停掉 `media-gateway`
2. 把宿主机 Plex / Emby Nginx 配置切回原来的直连版
3. `nginx -t && systemctl reload nginx`

Bot、数据库、Redis 和 WebApp 数据都不需要回滚。

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
