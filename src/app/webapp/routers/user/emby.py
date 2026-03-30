#!/usr/bin/env python3
"""用户 Emby 路由 - Emby 账户绑定和线路管理

注意: 此模块从 user_legacy.py 重新导出路由函数，以保持向后兼容性。
后续版本将逐步迁移实现代码到此模块。
"""

from fastapi import APIRouter

# 创建子路由（不添加前缀，由主路由统一管理）
router = APIRouter()

# 从 legacy 模块导入路由处理函数
# 这里暂时导入一个空路由，实际路由仍由 user_legacy.py 提供
# 在后续版本中，将逐步将 Emby 相关路由迁移到此处

# 占位符 - 实际路由通过 user_legacy.py 提供
# 以下注释列出了应属于此模块的路由：
# - POST /bind/emby - 绑定 Emby 账户
# - GET /emby_lines - 获取 Emby 线路列表
# - POST /bind/emby_line - 绑定 Emby 线路
# - POST /unbind/emby_line - 解绑 Emby 线路
# - POST /lines/emby/available - 获取可用 Emby 线路

__all__ = ["router"]
