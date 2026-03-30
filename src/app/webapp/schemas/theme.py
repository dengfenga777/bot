"""主题配置相关的数据模型"""

from pydantic import BaseModel, Field
from typing import Optional


class ThemeConfig(BaseModel):
    """主题配置模型"""

    # 主色调
    primary_color: str = Field(default="#9333ea", description="主色调")
    # 次要色调
    secondary_color: str = Field(default="#3b82f6", description="次要色调")
    # 成功色
    success_color: str = Field(default="#10b981", description="成功色")
    # 警告色
    warning_color: str = Field(default="#f59e0b", description="警告色")
    # 错误色
    error_color: str = Field(default="#ef4444", description="错误色")
    # 信息色
    info_color: str = Field(default="#3b82f6", description="信息色")

    # 背景颜色
    background_color: str = Field(default="#f9fafb", description="背景颜色")
    # 表面颜色（卡片等）
    surface_color: str = Field(default="#ffffff", description="表面颜色")

    # 字体大小设置
    font_size_base: int = Field(default=14, ge=10, le=20, description="基础字体大小(px)")
    font_size_title: int = Field(default=24, ge=16, le=36, description="标题字体大小(px)")
    font_size_subtitle: int = Field(
        default=16, ge=12, le=24, description="副标题字体大小(px)"
    )

    # 圆角大小
    border_radius: int = Field(default=8, ge=0, le=24, description="圆角大小(px)")

    # 主题模式
    theme_mode: str = Field(default="light", description="主题模式: light 或 dark")


class ThemeConfigUpdate(BaseModel):
    """主题配置更新模型"""

    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    success_color: Optional[str] = None
    warning_color: Optional[str] = None
    error_color: Optional[str] = None
    info_color: Optional[str] = None
    background_color: Optional[str] = None
    surface_color: Optional[str] = None
    font_size_base: Optional[int] = None
    font_size_title: Optional[int] = None
    font_size_subtitle: Optional[int] = None
    border_radius: Optional[int] = None
    theme_mode: Optional[str] = None


class ThemeConfigResponse(BaseModel):
    """主题配置响应模型"""

    config: ThemeConfig
    message: str = "主题配置获取成功"
