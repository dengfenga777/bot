import hashlib
import hmac
import json

from app.config import settings
from app.webapp.schemas import TelegramUser
from fastapi import HTTPException, Request, status


def verify_telegram_data(data: dict) -> bool:
    """验证来自 Telegram WebApp 的数据"""
    if "hash" not in data:
        return False

    received_hash = data["hash"]
    data_check = {k: v for k, v in data.items() if k != "hash"}

    # 按字母顺序排序键
    data_check_keys = sorted(data_check.keys())
    data_check_string = "\n".join([f"{k}={data_check[k]}" for k in data_check_keys])

    # 计算 HMAC-SHA-256 签名
    secret_key = hmac.new(
        b"WebAppData", settings.TG_API_TOKEN.encode(), digestmod=hashlib.sha256
    ).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), digestmod=hashlib.sha256
    ).hexdigest()

    # 验证哈希
    return calculated_hash == received_hash


def get_telegram_user(request: Request) -> TelegramUser:
    """从请求中获取和验证 Telegram 用户数据。

    支持三种模式：
    1) 正常的 Telegram WebApp，通过中间件注入 request.state.telegram_data
    2) 开发模式（DEBUG=true）下，允许使用开发头部模拟：
       - X-Dev-Tg-User-Id: 必填，整数
       - X-Dev-Tg-Username: 可选
       - X-Dev-Tg-First-Name: 可选
    3) 明确无认证时返回 401
    """
    try:
        # 开发模式：允许通过自定义头模拟用户
        if not hasattr(request.state, "telegram_data"):
            if settings.DEBUG:
                mock_id = request.headers.get("X-Dev-Tg-User-Id")
                if mock_id:
                    try:
                        mock_user = TelegramUser(
                            id=int(mock_id),
                            username=request.headers.get("X-Dev-Tg-Username"),
                            first_name=request.headers.get("X-Dev-Tg-First-Name") or "Dev",
                            is_premium=False,
                        )
                        return mock_user
                    except Exception:
                        pass
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要 Telegram 认证",
            )

        # 从中间件注入的数据解析用户信息
        user_data = request.state.telegram_data.get("user")
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 Telegram 用户数据",
            )

        # 检查是否是模拟数据
        if request.state.telegram_data.get("hash") == "mock_hash_for_development":
            user_dict = json.loads(user_data)
            return TelegramUser(**user_dict)

        # 正常的 Telegram 数据
        return TelegramUser(**json.loads(user_data))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"获取用户数据失败: {str(e)}",
        )
