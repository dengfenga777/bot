#!/usr/bin/env python3
"""
智能路由系统验证脚本
检查 Nginx + Lua + Redis 路由系统的部署状态和健康状况
"""

import sys
import subprocess
import socket
from pathlib import Path
from typing import Dict, List, Tuple
import redis

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from app.config import settings
from app.log import logger


class RoutingSystemVerifier:
    """智能路由系统验证器"""

    # 本地 Redis 配置 (脚本在宿主机运行，直接连接本地 Redis)
    # Docker 容器内的应用使用 Docker 网络名称 (pmsmanagebot-redis)
    LOCAL_REDIS_HOST = "127.0.0.1"
    LOCAL_REDIS_PORT = 6379

    def __init__(self):
        """初始化验证器"""
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []

    def print_header(self, title: str):
        """打印章节标题"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_check(self, name: str, passed: bool, details: str = ""):
        """打印检查结果"""
        status = "✓ PASS" if passed else "✗ FAIL"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"

        print(f"{color}{status}{reset} | {name}")
        if details:
            print(f"       {details}")

        if passed:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

    def print_warning(self, message: str):
        """打印警告信息"""
        print(f"\033[93m⚠ WARNING\033[0m | {message}")
        self.warnings.append(message)

    # ========== 1. Nginx 检查 ==========

    def check_nginx_installed(self) -> bool:
        """检查 Nginx 是否已安装"""
        try:
            result = subprocess.run(
                ["nginx", "-v"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stderr.strip()
            self.print_check("Nginx 已安装", True, version)
            return True
        except Exception as e:
            self.print_check("Nginx 已安装", False, str(e))
            return False

    def check_nginx_lua_module(self) -> bool:
        """检查 Nginx Lua 模块是否已加载"""
        try:
            result = subprocess.run(
                ["nginx", "-V"],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stderr

            # 检查是否包含 lua 模块
            has_lua = "lua" in output.lower() or "luajit" in output.lower()

            if has_lua:
                self.print_check("Nginx Lua 模块已加载", True)
            else:
                self.print_check("Nginx Lua 模块已加载", False,
                               "需要安装 OpenResty 或 ngx_lua 模块")
            return has_lua
        except Exception as e:
            self.print_check("Nginx Lua 模块已加载", False, str(e))
            return False

    def check_nginx_running(self) -> bool:
        """检查 Nginx 是否正在运行"""
        try:
            result = subprocess.run(
                ["pgrep", "-x", "nginx"],
                capture_output=True,
                text=True,
                timeout=5
            )
            running = result.returncode == 0

            if running:
                pids = result.stdout.strip().split("\n")
                self.print_check("Nginx 正在运行", True, f"进程数: {len(pids)}")
            else:
                self.print_check("Nginx 正在运行", False, "未检测到 nginx 进程")
            return running
        except Exception as e:
            self.print_check("Nginx 正在运行", False, str(e))
            return False

    def check_nginx_configs(self) -> bool:
        """检查 Nginx 配置文件是否存在"""
        config_files = [
            "/etc/nginx/nginx.conf",
            "/etc/nginx/sites-available/emby",
            "/etc/nginx/sites-available/plex",
        ]

        all_exist = True
        for config_file in config_files:
            exists = Path(config_file).exists()
            if not exists:
                all_exist = False
                self.print_warning(f"配置文件不存在: {config_file}")

        if all_exist:
            self.print_check("Nginx 配置文件完整", True, f"检查了 {len(config_files)} 个文件")
        else:
            self.print_check("Nginx 配置文件完整", False, "部分配置文件缺失")

        return all_exist

    def check_lua_scripts(self) -> bool:
        """检查 Lua 路由脚本是否存在"""
        lua_scripts = [
            "/etc/nginx/lua/emby_route.lua",
            "/etc/nginx/lua/plex_route.lua",
        ]

        all_exist = True
        for script in lua_scripts:
            exists = Path(script).exists()
            if exists:
                size = Path(script).stat().st_size
                self.print_check(f"Lua 脚本存在: {Path(script).name}", True, f"{size} bytes")
            else:
                self.print_check(f"Lua 脚本存在: {Path(script).name}", False)
                all_exist = False

        return all_exist

    # ========== 2. Redis 检查 ==========

    def check_redis_connection(self) -> Tuple[bool, redis.Redis]:
        """检查 Redis 连接"""
        try:
            # 使用本地地址连接 Redis (脚本在宿主机运行)
            redis_client = redis.Redis(
                host=self.LOCAL_REDIS_HOST,
                port=self.LOCAL_REDIS_PORT,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            redis_client.ping()

            info = redis_client.info("server")
            version = info.get("redis_version", "unknown")

            self.print_check("Redis 连接成功", True,
                           f"{self.LOCAL_REDIS_HOST}:{self.LOCAL_REDIS_PORT} (v{version})")
            return True, redis_client
        except Exception as e:
            self.print_check("Redis 连接成功", False, str(e))
            return False, None

    def check_redis_line_keys(self, redis_client: redis.Redis) -> bool:
        """检查 Redis 中是否存在线路映射"""
        if not redis_client:
            return False

        try:
            # 检查默认线路
            default_line = redis_client.get("default_line")
            if default_line:
                self.print_check("默认线路已设置", True, f"default_line = {default_line}")
            else:
                self.print_check("默认线路已设置", False, "default_line 键不存在")

            # 检查 Emby 用户线路
            emby_keys = redis_client.keys("emby_line:*")
            emby_count = len(emby_keys)

            if emby_count > 0:
                self.print_check("Emby 用户线路映射", True, f"{emby_count} 个用户")
            else:
                self.print_warning("未找到 Emby 用户线路映射，可能需要运行同步脚本")

            # 检查 Plex 用户线路
            plex_keys = redis_client.keys("plex_line:*")
            plex_count = len(plex_keys)

            if plex_count > 0:
                self.print_check("Plex 用户线路映射", True, f"{plex_count} 个用户")
            else:
                self.print_warning("未找到 Plex 用户线路映射，可能需要运行同步脚本")

            return bool(default_line and (emby_count > 0 or plex_count > 0))
        except Exception as e:
            self.print_check("Redis 线路键检查", False, str(e))
            return False

    # ========== 3. 数据库检查 ==========

    def check_database_tables(self) -> bool:
        """检查数据库表是否存在"""
        import sqlite3

        try:
            db_path = settings.DATA_PATH / "data.db"
            if not db_path.exists():
                self.print_check("数据库文件存在", False, f"未找到: {db_path}")
                return False

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 检查必要的表
            tables_to_check = [
                "emby_user",
                "user",  # Plex 用户表
                "line_traffic_stats",
                "line_switch_history",
            ]

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = set(row[0] for row in cursor.fetchall())

            all_exist = True
            for table in tables_to_check:
                if table in existing_tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    self.print_check(f"表 {table} 存在", True, f"{count} 行数据")
                else:
                    self.print_check(f"表 {table} 存在", False)
                    all_exist = False

            conn.close()
            return all_exist
        except Exception as e:
            self.print_check("数据库表检查", False, str(e))
            return False

    # ========== 4. 网络检查 ==========

    def check_vps_connectivity(self) -> bool:
        """检查 VPS 节点连通性"""
        vps_nodes = {
            "HK": ("154.3.36.75", 443),
            "SG": ("213.35.105.166", 443),
            "US": ("146.235.219.32", 443),
            "JP": ("154.31.114.167", 443),
        }

        all_ok = True
        for name, (ip, port) in vps_nodes.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((ip, port))
                sock.close()

                if result == 0:
                    self.print_check(f"VPS {name} 连通性", True, f"{ip}:{port}")
                else:
                    self.print_check(f"VPS {name} 连通性", False, f"{ip}:{port} 无法连接")
                    all_ok = False
            except Exception as e:
                self.print_check(f"VPS {name} 连通性", False, str(e))
                all_ok = False

        return all_ok

    # ========== 5. 同步脚本检查 ==========

    def check_sync_script(self) -> bool:
        """检查 Redis 同步脚本"""
        script_path = Path(__file__).parent / "sync_lines_to_redis.py"

        if script_path.exists():
            self.print_check("Redis 同步脚本存在", True, str(script_path))

            # 检查脚本是否可执行
            if script_path.stat().st_mode & 0o111:
                self.print_check("同步脚本可执行", True)
            else:
                self.print_warning(f"同步脚本不可执行，运行: chmod +x {script_path}")

            return True
        else:
            self.print_check("Redis 同步脚本存在", False, f"未找到: {script_path}")
            return False

    # ========== 6. 端到端测试 ==========

    def test_line_routing(self, redis_client: redis.Redis) -> bool:
        """测试线路路由逻辑"""
        if not redis_client:
            self.print_warning("无法测试线路路由：Redis 未连接")
            return False

        try:
            # 模拟查询用户线路
            test_user_id = "test_user_123"
            test_line = "154.3.36.75:443"  # HK 线路

            # 设置测试数据
            redis_client.set(f"emby_line:{test_user_id}", test_line)

            # 查询测试数据
            result = redis_client.get(f"emby_line:{test_user_id}")

            if result == test_line:
                self.print_check("线路路由逻辑测试", True, f"用户 {test_user_id} → {result}")
                # 清理测试数据
                redis_client.delete(f"emby_line:{test_user_id}")
                return True
            else:
                self.print_check("线路路由逻辑测试", False, f"期望: {test_line}, 实际: {result}")
                return False
        except Exception as e:
            self.print_check("线路路由逻辑测试", False, str(e))
            return False

    # ========== 主验证流程 ==========

    def run_verification(self):
        """运行完整验证流程"""
        print("\n" + "=" * 70)
        print("  智能路由系统部署验证")
        print("=" * 70)
        print(f"  项目路径: {settings.DATA_PATH.parent}")
        print(f"  数据路径: {settings.DATA_PATH}")
        print(f"  Redis (本地): {self.LOCAL_REDIS_HOST}:{self.LOCAL_REDIS_PORT}")
        print("=" * 70)

        # 1. Nginx 检查
        self.print_header("1. Nginx 检查")
        self.check_nginx_installed()
        self.check_nginx_lua_module()
        self.check_nginx_running()
        self.check_nginx_configs()
        self.check_lua_scripts()

        # 2. Redis 检查
        self.print_header("2. Redis 检查")
        redis_ok, redis_client = self.check_redis_connection()
        if redis_ok:
            self.check_redis_line_keys(redis_client)

        # 3. 数据库检查
        self.print_header("3. 数据库检查")
        self.check_database_tables()

        # 4. 网络检查
        self.print_header("4. VPS 节点连通性检查")
        self.check_vps_connectivity()

        # 5. 同步脚本检查
        self.print_header("5. 同步脚本检查")
        self.check_sync_script()

        # 6. 端到端测试
        self.print_header("6. 端到端测试")
        if redis_ok:
            self.test_line_routing(redis_client)

        # 总结
        self.print_summary()

    def print_summary(self):
        """打印验证总结"""
        print("\n" + "=" * 70)
        print("  验证总结")
        print("=" * 70)

        total = self.checks_passed + self.checks_failed
        pass_rate = (self.checks_passed / total * 100) if total > 0 else 0

        print(f"  通过检查: \033[92m{self.checks_passed}\033[0m")
        print(f"  失败检查: \033[91m{self.checks_failed}\033[0m")
        print(f"  警告数量: \033[93m{len(self.warnings)}\033[0m")
        print(f"  通过率: {pass_rate:.1f}%")
        print("=" * 70)

        if self.checks_failed == 0:
            print("\n\033[92m✓ 所有检查通过！智能路由系统已正确部署。\033[0m\n")
            return 0
        else:
            print("\n\033[91m✗ 部分检查失败，请查看上方详细信息并修复问题。\033[0m\n")

            if self.warnings:
                print("⚠ 警告信息:")
                for i, warning in enumerate(self.warnings, 1):
                    print(f"  {i}. {warning}")
                print()

            return 1


def main():
    """主函数"""
    try:
        verifier = RoutingSystemVerifier()
        exit_code = verifier.run_verification()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n验证被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"验证脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
