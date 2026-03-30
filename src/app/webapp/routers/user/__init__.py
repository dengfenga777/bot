#!/usr/bin/env python3
"""
用户路由模块 - 模块化的用户相关 API 端点

该模块将原有的大型 user.py 按功能拆分为多个子模块：
- core.py: 核心用户信息（dashboard, info, activities）
- plex.py: Plex 绑定和线路管理（待迁移）
- emby.py: Emby 绑定和线路管理（待迁移）
- lines.py: 通用线路管理操作（待迁移）
- nsfw.py: NSFW 内容权限管理
- credits.py: 积分转账操作

当前采用渐进式迁移策略：
- 已迁移的路由从子模块导入
- 未迁移的路由仍从 user_legacy.py 导入

使用方式保持不变：
    from app.webapp.routers.user import router
"""

# 为保持向后兼容性，直接从 user_legacy.py 导入完整的 router
# 这确保所有现有路由继续正常工作
# 后续版本将逐步将路由迁移到子模块
from app.webapp.routers.user_legacy import router

# 导出子模块（使用相对导入避免循环导入）
from . import core, plex, emby, credits

__all__ = ["router", "core", "plex", "emby", "credits"]
