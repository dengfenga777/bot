#!/usr/bin/env python3
"""
应用程序自定义异常层次结构

提供更精确的异常处理，替代宽泛的 Exception 捕获。
使用方式：
    from app.exceptions import UserNotFoundError, CreditsInsufficientError

    try:
        user = get_user(tg_id)
    except UserNotFoundError:
        # 处理用户不存在
    except DatabaseError:
        # 处理数据库错误
"""


class PMSBotError(Exception):
    """应用程序基础异常类"""

    def __init__(self, message: str = "发生未知错误", code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(self.message)


# ============ 数据库相关异常 ============


class DatabaseError(PMSBotError):
    """数据库操作错误"""

    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(message, "DB_ERROR")


class RecordNotFoundError(DatabaseError):
    """记录未找到"""

    def __init__(self, entity: str = "记录", identifier: str = ""):
        message = f"{entity}未找到" + (f": {identifier}" if identifier else "")
        super().__init__(message)
        self.code = "NOT_FOUND"


class DuplicateRecordError(DatabaseError):
    """记录重复"""

    def __init__(self, entity: str = "记录"):
        super().__init__(f"{entity}已存在")
        self.code = "DUPLICATE"


# ============ 用户相关异常 ============


class UserError(PMSBotError):
    """用户相关错误"""

    pass


class UserNotFoundError(UserError):
    """用户未找到"""

    def __init__(self, user_id: int | str = ""):
        message = f"用户未找到" + (f": {user_id}" if user_id else "")
        super().__init__(message, "USER_NOT_FOUND")


class UserAlreadyBoundError(UserError):
    """用户已绑定"""

    def __init__(self, service: str = ""):
        message = f"用户已绑定{service}账户" if service else "用户已绑定"
        super().__init__(message, "USER_ALREADY_BOUND")


class UserNotBoundError(UserError):
    """用户未绑定"""

    def __init__(self, service: str = ""):
        message = f"用户未绑定{service}账户" if service else "用户未绑定"
        super().__init__(message, "USER_NOT_BOUND")


# ============ 积分相关异常 ============


class CreditsError(PMSBotError):
    """积分相关错误"""

    pass


class CreditsInsufficientError(CreditsError):
    """积分不足"""

    def __init__(self, required: float = 0, available: float = 0):
        message = f"积分不足"
        if required and available:
            message += f"（需要 {required:.2f}，当前 {available:.2f}）"
        super().__init__(message, "CREDITS_INSUFFICIENT")
        self.required = required
        self.available = available


class CreditsTransferError(CreditsError):
    """积分转账错误"""

    def __init__(self, message: str = "积分转账失败"):
        super().__init__(message, "CREDITS_TRANSFER_FAILED")


# ============ 媒体服务器相关异常 ============


class MediaServerError(PMSBotError):
    """媒体服务器错误"""

    pass


class PlexError(MediaServerError):
    """Plex 服务器错误"""

    def __init__(self, message: str = "Plex 服务器错误"):
        super().__init__(message, "PLEX_ERROR")


class EmbyError(MediaServerError):
    """Emby 服务器错误"""

    def __init__(self, message: str = "Emby 服务器错误"):
        super().__init__(message, "EMBY_ERROR")


class ConnectionError(MediaServerError):
    """连接错误"""

    def __init__(self, service: str = "", message: str = ""):
        msg = f"无法连接到{service}" if service else "连接失败"
        if message:
            msg += f": {message}"
        super().__init__(msg, "CONNECTION_ERROR")


# ============ 权限相关异常 ============


class PermissionError(PMSBotError):
    """权限错误"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(message, "PERMISSION_DENIED")


class NSFWAlreadyUnlockedError(PermissionError):
    """NSFW 已解锁"""

    def __init__(self):
        super().__init__("您已拥有全部库权限")
        self.code = "NSFW_ALREADY_UNLOCKED"


class NSFWNotUnlockedError(PermissionError):
    """NSFW 未解锁"""

    def __init__(self):
        super().__init__("您未解锁 NSFW 内容")
        self.code = "NSFW_NOT_UNLOCKED"


# ============ 邀请码相关异常 ============


class InvitationError(PMSBotError):
    """邀请码错误"""

    pass


class InvitationCodeInvalidError(InvitationError):
    """邀请码无效"""

    def __init__(self, code: str = ""):
        message = f"邀请码无效" + (f": {code}" if code else "")
        super().__init__(message, "INVITATION_INVALID")


class InvitationCodeUsedError(InvitationError):
    """邀请码已使用"""

    def __init__(self, code: str = ""):
        message = f"邀请码已被使用" + (f": {code}" if code else "")
        super().__init__(message, "INVITATION_USED")


# ============ 验证相关异常 ============


class ValidationError(PMSBotError):
    """验证错误"""

    def __init__(self, field: str = "", message: str = "验证失败"):
        msg = f"{field}: {message}" if field else message
        super().__init__(msg, "VALIDATION_ERROR")


class InvalidParameterError(ValidationError):
    """参数无效"""

    def __init__(self, param: str = "", message: str = ""):
        msg = f"参数 {param} 无效" if param else "参数无效"
        if message:
            msg += f": {message}"
        super().__init__(message=msg)
        self.code = "INVALID_PARAMETER"


# ============ 配置相关异常 ============


class ConfigurationError(PMSBotError):
    """配置错误"""

    def __init__(self, message: str = "配置错误"):
        super().__init__(message, "CONFIG_ERROR")


class FeatureDisabledError(ConfigurationError):
    """功能已禁用"""

    def __init__(self, feature: str = ""):
        message = f"{feature}功能已禁用" if feature else "该功能已禁用"
        super().__init__(message)
        self.code = "FEATURE_DISABLED"
