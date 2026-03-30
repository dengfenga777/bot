#!/usr/bin/env python3
"""用户 Plex 路由 - Plex 账户绑定和线路管理

注意: 此模块从 user_legacy.py 重新导出路由函数，以保持向后兼容性。
后续版本将逐步迁移实现代码到此模块。
"""

from fastapi import APIRouter

# 创建子路由（不添加前缀，由主路由统一管理）
router = APIRouter()

# 从 legacy 模块导入路由处理函数
# 这里暂时导入一个空路由，实际路由仍由 user_legacy.py 提供
# 在后续版本中，将逐步将 Plex 相关路由迁移到此处

# 占位符 - 实际路由通过 user_legacy.py 提供
# 以下注释列出了应属于此模块的路由：
# - POST /bind/plex - 绑定 Plex 账户
# - GET /plex_lines - 获取 Plex 线路列表
# - POST /bind/plex_line - 绑定 Plex 线路
# - POST /unbind/plex_line - 解绑 Plex 线路
# - POST /lines/plex/available - 获取可用 Plex 线路

__all__ = ["router"]
