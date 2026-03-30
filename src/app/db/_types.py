#!/usr/bin/env python3
"""数据库模块类型定义"""

import sqlite3
from typing import Protocol


class HasDBConnection(Protocol):
    """定义数据库连接接口的 Protocol

    用于 Mixin 类的类型提示，确保 Mixin 能正确访问 con 和 cur 属性。
    """

    @property
    def con(self) -> sqlite3.Connection:
        """获取数据库连接"""
        ...

    @property
    def cur(self) -> sqlite3.Cursor:
        """获取数据库游标"""
        ...
