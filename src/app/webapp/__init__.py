import secrets
from pathlib import Path

from app.config import settings
from app.log import logger
from app.webapp.middlewares import TelegramAuthMiddleware
from app.webapp.routers import (
    checkin_router,
    medals_router,
    rankings_router,
    system_router,
    user_router,
)
from app.webapp.routers.activities.auction import router as auction_router
from app.webapp.routers.activities.blackjack import router as blackjack_router
from app.webapp.routers.activities.luckywheel import router as luckywheel_router
from app.webapp.routers.admin import router as admin_router
from app.webapp.routers.invitation import router as invitation_router
from app.webapp.routers.theme import router as theme_router
from app.webapp.startup.lifespan import lifespan
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

# 创建 FastAPI 应用
app = FastAPI(
    title="PMSManageBot API",
    description="API for PMSManageBot WebApp",
    lifespan=lifespan,
)

# 配置限流
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 配置 SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.WEBAPP_SESSION_SECRET_KEY
    if hasattr(settings, "WEBAPP_SESSION_SECRET_KEY")
    else secrets.token_urlsafe(32),
    session_cookie="pmsmanagebot_session",
    max_age=86400,  # 1天过期
)

# 配置 CORS - 仅允许特定来源
allowed_origins = [
    settings.WEBAPP_URL,
    "https://web.telegram.org",
]
# 开发环境允许 localhost
if settings.LOG_LEVEL == "DEBUG":
    allowed_origins.extend(["http://localhost:8080", "http://127.0.0.1:8080"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "X-Telegram-Init-Data", "Authorization"],
)

# 添加 Telegram 认证中间件
app.add_middleware(TelegramAuthMiddleware)


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "message": "PMSManageBot is running"}


# 注册路由
app.include_router(user_router)
app.include_router(rankings_router)
app.include_router(system_router)  # 添加系统统计路由
app.include_router(invitation_router)  # 添加邀请码路由
app.include_router(admin_router)  # 添加管理员路由
app.include_router(luckywheel_router, prefix="/api")  # 添加幸运大转盘路由
app.include_router(auction_router, prefix="/api")  # 添加竞拍活动路由
app.include_router(blackjack_router, prefix="/api")  # 添加21点游戏路由
app.include_router(theme_router, prefix="/api")  # 添加主题配置路由
app.include_router(medals_router, prefix="/api")  # 添加勋章系统路由
app.include_router(checkin_router, prefix="/api")  # 添加签到路由


def setup_static_files():
    """配置静态文件服务"""
    static_dir = Path(settings.WEBAPP_STATIC_DIR).absolute()
    if not static_dir.exists():
        logger.warning(f"WebApp 静态文件目录不存在: {static_dir}")
        return False

    try:
        # pics
        app.mount(
            "/pics",
            StaticFiles(directory=str(settings.TG_USER_PROFILE_CACHE_PATH.absolute())),
            name="pics",
        )
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="webapp")
        return True
    except Exception as e:
        logger.error(f"挂载 WebApp 静态文件失败: {e}")
        return False


# 生产环境下 gunicorn 直接加载 app.webapp:app，不会经过 main.py 的 start_api_server。
# 在模块导入阶段尝试挂载静态资源，确保 /、/medals、/pics 等路径可用。
setup_static_files()
