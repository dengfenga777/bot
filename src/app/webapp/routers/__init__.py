from app.webapp.routers.checkin import router as checkin_router
from app.webapp.routers.medals import router as medals_router
from app.webapp.routers.rankings import router as rankings_router
from app.webapp.routers.system import router as system_router
from app.webapp.routers.user import router as user_router

__all__ = [
    "user_router",
    "rankings_router",
    "system_router",
    "medals_router",
    "checkin_router",
]
