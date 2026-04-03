from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class TelegramUser(BaseModel):
    """Telegram 用户信息模型"""

    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    is_bot: bool = False
    is_premium: bool = False


class SharedProxyProfile(BaseModel):
    """共享反代配置模型"""

    domain: str
    port: int = 443
    enabled: bool = False
    verification_status: str = "unknown"
    verified_at: Optional[int] = None
    last_error: Optional[str] = None
    updated_at: Optional[int] = None
    target: Optional[str] = None
    url: Optional[str] = None


class UserInfo(BaseModel):
    """用户完整信息模型"""

    tg_id: int
    display_name: Optional[str] = None
    credits: float = 0
    donation: float = 0
    medal_multiplier: float = 1.0
    medals: List[Dict[str, Any]] = []
    invitation_codes: List[str] = []
    invited_count: int = 0
    plex_info: Optional[Dict[str, Any]] = None
    emby_info: Optional[Dict[str, Any]] = None
    overseerr_info: Optional[Dict[str, Any]] = None
    shared_proxy: Optional[SharedProxyProfile] = None
    is_admin: bool = False


class BaseResponse(BaseModel):
    """通用响应模型"""

    success: bool
    message: str


class BindPlexRequest(BaseModel):
    """绑定Plex请求模型"""

    email: EmailStr


class BindEmbyRequest(BaseModel):
    """绑定Emby请求模型"""

    username: str = Field(..., min_length=2)


class EmbyLineRequest(BaseModel):
    """Emby线路请求模型"""

    line: str = Field(..., min_length=1)


class PlexLineRequest(BaseModel):
    """Plex线路请求模型"""

    line: str = Field(..., min_length=1)


class EmbyLineInfo(BaseModel):
    """Emby线路信息模型"""

    name: str
    tags: List[str] = []
    is_premium: bool = False


class PlexLineInfo(BaseModel):
    """Plex线路信息模型"""

    name: str
    tags: List[str] = []
    is_premium: bool = False


class EmbyLinesResponse(BaseResponse):
    """Emby线路列表响应模型"""

    lines: List[EmbyLineInfo]


class PlexLinesResponse(BaseResponse):
    """Plex线路列表响应模型"""

    lines: List[PlexLineInfo]


class LineTagRequest(BaseModel):
    """线路标签请求模型"""

    line_name: str = Field(..., min_length=1)
    tags: List[str] = Field(..., min_items=0)


class LineTagResponse(BaseModel):
    """线路标签响应模型"""

    line_name: str
    tags: List[str]


class AllLineTagsResponse(BaseModel):
    """所有线路标签响应模型"""

    lines: Dict[str, List[str]]


class AuthBindLineRequest(BaseModel):
    """认证并绑定线路的请求模型"""

    username: str = Field(..., min_length=1, description="用户名或邮箱")
    password: Optional[str] = Field(None, description="密码")
    line: str = Field(..., min_length=1, description="要绑定的线路名称")
    token: Optional[str] = Field(None, description="用户认证令牌")
    auth_method: Optional[str] = Field(
        None, description="认证方法，支持 'password' 或 'token'"
    )


class CreditsTransferRequest(BaseModel):
    """积分转移请求模型"""

    target_tg_id: int = Field(..., description="目标用户的 Telegram ID")
    amount: float = Field(
        ..., gt=0, le=10000, description="转移积分数量，必须大于0且不超过10000"
    )
    note: Optional[str] = Field(None, max_length=200, description="转移备注，可选")


class CreditsTransferResponse(BaseModel):
    """积分转移响应模型"""

    success: bool
    message: str
    transferred_amount: Optional[float] = None
    fee_amount: Optional[float] = None
    current_credits: Optional[float] = None


class ChangeTgBindingRequest(BaseModel):
    """管理员 TG 换绑请求"""

    old_tg_id: Optional[int] = Field(
        None, gt=0, description="原 TG ID；不知道时可改用 Plex/Emby 账号信息定位"
    )
    new_tg_id: int = Field(..., gt=0, description="新的 TG ID")
    plex_email: Optional[EmailStr] = Field(
        None, description="可选：用 Plex 邮箱定位当前绑定"
    )
    plex_username: Optional[str] = Field(
        None, min_length=1, description="可选：用 Plex 用户名定位当前绑定"
    )
    emby_username: Optional[str] = Field(
        None, min_length=1, description="可选：用 Emby 用户名定位当前绑定"
    )
    note: Optional[str] = Field(None, max_length=200, description="备注信息，可选")


class CurrentLineResponse(BaseModel):
    """当前绑定线路响应模型"""

    success: bool
    message: str
    line: Optional[str] = None


class SharedProxyRequest(BaseModel):
    """共享反代保存请求"""

    domain: str = Field(..., min_length=1, max_length=255)


class SharedProxyResponse(BaseResponse):
    """共享反代配置响应"""

    shared_proxy: Optional[SharedProxyProfile] = None
