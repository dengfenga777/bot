#!/usr/bin/env python3
"""
数据库模块 - 模块化的数据库操作

该模块将原有的大型 db.py 按功能拆分为多个子模块：
- base.py: 基础连接管理和表创建
- user.py: 用户相关操作
- credits.py: 积分和统计相关操作
- invitation.py: 邀请码相关操作
- line.py: 线路和媒体库相关操作
- _types.py: 类型定义

使用方式保持不变：
    from app.db import DB
    db = DB()
    db.get_user_credits(tg_id)

新增的模块化导入方式：
    from app.db.user import UserMixin
    from app.db.credits import CreditsMixin

类型提示导入：
    from app.db._types import HasDBConnection
"""

# 为了向后兼容，从原有的 db.py 导入 DB 类
# 这样所有现有代码的 `from app.db import DB` 仍然有效
from app.db_legacy import DB

# 同时导出 Mixin 类供需要时使用
from app.db.base import DBBase
from app.db.user import UserMixin
from app.db.credits import CreditsMixin
from app.db.invitation import InvitationMixin
from app.db.line import LineMixin
from app.db._types import HasDBConnection

__all__ = [
    "DB",
    "DBBase",
    "UserMixin",
    "CreditsMixin",
    "InvitationMixin",
    "LineMixin",
    "HasDBConnection",
]
