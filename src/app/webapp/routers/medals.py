"""勋章商店与用户勋章 API"""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.db import DB
from app.webapp.auth import get_telegram_user
from app.webapp.middlewares import require_telegram_auth
from app.webapp.schemas import TelegramUser

router = APIRouter(prefix="/medals", tags=["medals"])


@router.get("/shop")
@require_telegram_auth
async def get_medal_shop(
    request: Request,
    user: TelegramUser = Depends(get_telegram_user),
):
    """获取勋章商店和当前用户勋章信息"""
    db = DB()
    try:
        return {"success": True, "data": db.get_medal_shop_payload(user.id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取勋章商店失败: {str(e)}")
    finally:
        db.close()


@router.post("/shop/{medal_code}/purchase")
@require_telegram_auth
async def purchase_medal(
    medal_code: str,
    request: Request,
    user: TelegramUser = Depends(get_telegram_user),
):
    """购买勋章"""
    db = DB()
    try:
        success, message, payload = db.purchase_medal(user.id, medal_code)
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"success": True, "message": message, "data": payload}
    finally:
        db.close()
