import os
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from app.utils.system import SystemUtils
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # log
    LOG_LEVEL: str = "INFO"

    # app name
    SITE_NAME: str = "PMS"

    # data folder
    DATA_DIR: str = ""

    # plex
    PLEX_REGISTER: bool = False
    PLEX_BASE_URL: str = ""
    PLEX_API_TOKEN: str = ""
    PLEX_ADMIN_USER: str = ""
    PLEX_ADMIN_EMAIL: str = ""
    PLEX_PUBLIC_HOST: str = "plex.misaya.org"
    PLEX_ORIGIN_HOST: str = "plex-origin.misaya.org"

    # Overseerr
    OVERSEERR_BASE_URL: str = ""
    OVERSEERR_API_TOKEN: str = ""


    # credits
    INVITATION_CREDITS: int = 288
    DONATION_MULTIPLIER: int = 5  # 捐赠积分倍数
    DUAL_BIND_MULTIPLIER: float = 1.5  # 双账号绑定积分加成倍数
    ABUSE_WATCH_THRESHOLD: int = 16  # 异常观看判定阈值（小时/天）

    # --- Removed features (stubs for backward compatibility) ---
    NSFW_LIBS: list = []
    UNLOCK_CREDITS: int = 0
    PREMIUM_DAILY_CREDITS: int = 0
    USER_TRAFFIC_LIMIT: int = 0
    PREMIUM_USER_TRAFFIC_LIMIT: int = 0
    CREDITS_COST_PER_10GB: int = 0
    PREMIUM_UNLOCK_ENABLED: bool = False
    STREAM_BACKEND: list = []
    PREMIUM_STREAM_BACKEND: list = []
    PREMIUM_FREE: bool = False
    REDIS_LINE_TRAFFIC_STATS_HANDLE_SIZE: int = 100

    CREDITS_TRANSFER_ENABLED: bool = True  # 积分转移功能开关

    # 签到功能
    CHECKIN_ENABLED: bool = True            # 是否开启每日签到
    CHECKIN_MONTHLY_TOP3_REWARD: float = 20.0  # 月度签到前三名奖励积分

    # 换绑欠积分
    DEBT_MAX_MONTHS: int = 3                # 欠积分最多允许多少个月

    # TG
    TG_API_TOKEN: str = ""
    TG_ADMIN_CHAT_ID: list[str] = []
    TG_PRIVILEGED_USERS: list[int] = []  # 特权用户列表（不受群组离开限制）
    TG_GROUP: str = ""
    TG_CHANNEL: str = ""  # 可选的通知频道链接，如果不设置将使用群组链接

    # WebApp
    WEBAPP_ENABLE: bool = True  # 是否启用 WebApp
    WEBAPP_URL: str = "https://yourdomain.com"  # WebApp 的公开 URL，只接受环境变量
    WEBAPP_PORT: int = 6000  # WebApp 服务器监听端口
    WEBAPP_HOST: str = "0.0.0.0"  # WebApp 服务器监听地址
    WEBAPP_STATIC_DIR: str = (
        "webapp-frontend/dist"
        if not SystemUtils.is_container()
        else "/app/webapp-frontend/dist"
    )  # WebApp 前端静态文件目录
    SESSION_SECRET_KEY: str = ""  # 用于会话加密的密钥

    # tautulli
    TAUTULLI_URL: str = ""
    TAUTULLI_APIKEY: str = ""
    TAUTULLI_PUBLIC_URL: str = "/"
    TAUTULLI_VERIFY_SSL: bool = False

    # emby
    EMBY_REGISTER: bool = True
    EMBY_BASE_URL: str = ""
    EMBY_ENTRY_URL: str = ""  # 可指定 Emby 入口 URL，默认与 EMBY_BASE_URL 相同
    EMBY_ADMIN_URL: str = ""  # 用于 admin 插件（如 user_usage_stats）的 URL，默认与 EMBY_BASE_URL 相同
    EMBY_API_TOKEN: str = ""
    EMBY_ADMIN_USER: str = ""
    EMBY_USER_TEMPLATE: str = ""
    EMBY_USER_IS_HIDDEN: bool = True  # 新用户是否在登录界面隐藏
    EMBY_PUBLIC_HOST: str = "emby.misaya.org"
    EMBY_ORIGIN_HOST: str = "emby-origin.misaya.org"


    # redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    MEDIA_ROUTE_SIGNING_SECRET: str = ""
    MEDIA_ROUTE_SIGN_TTL: int = 90

    # redeem code
    PRIVILEGED_CODES: list[str] = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATA_PATH.exists():
            self.DATA_PATH.mkdir(parents=True)
        # 启动时尝试从配置文件加载设置
        self.load_config_from_file()

    # 设置北京时间
    @property
    def TZ(self):
        return timezone(timedelta(hours=8))

    @property
    def DATA_PATH(self):
        if not self.DATA_DIR:
            return (
                Path(__file__).parents[2] / "data"
                if not SystemUtils.is_container()
                else Path("/app/data")
            )
        return Path(self.DATA_DIR)

    @property
    def TG_USER_INFO_CACHE_PATH(self):
        return self.DATA_PATH / "tg_user_info.cache"

    @property
    def TG_USER_PROFILE_CACHE_PATH(self):
        path = Path(self.DATA_PATH) / "pics"
        if self.WEBAPP_ENABLE and Path(self.WEBAPP_STATIC_DIR).exists():
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def ENV_FILE_PATH(self):
        """环境变量文件路径"""
        return self.DATA_PATH / ".env"

    def load_config_from_file(self):
        """从配置文件加载设置"""
        # 从 .env 文件加载
        if self.ENV_FILE_PATH.exists():
            self._load_from_env_file()

    def _load_from_env_file(self):
        """从 .env 文件加载环境变量"""

        ignore_env = [
            "WEBAPP_URL",
        ]
        try:
            with open(self.ENV_FILE_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")

                        if key in ignore_env:
                            continue

                        # 设置环境变量
                        os.environ[key] = value

                        # 如果是当前设置中存在的字段，直接更新
                        if hasattr(self, key):
                            # 处理不同类型的值
                            current_value = getattr(self, key)
                            if isinstance(current_value, bool):
                                setattr(
                                    self,
                                    key,
                                    value.lower() in ("true", "1", "yes", "on"),
                                )
                            elif isinstance(current_value, int):
                                setattr(self, key, int(value))
                            elif isinstance(current_value, list):
                                # 支持 JSON 数组格式 ["a","b"] 和逗号分隔格式 a,b
                                import json as _json
                                raw = value.strip()
                                if raw.startswith("["):
                                    try:
                                        value = _json.loads(raw)
                                    except _json.JSONDecodeError:
                                        value = [item.strip() for item in value.split(",") if item.strip()]
                                else:
                                    value = [item.strip() for item in value.split(",") if item.strip()]
                                if key == "TG_ADMIN_CHAT_ID":
                                    value = [int(item) for item in value if str(item).strip('"').isdigit()]
                                elif key == "TG_PRIVILEGED_USERS":
                                    value = [int(item) for item in value if str(item).strip('"').isdigit()]
                                setattr(self, key, value)
                            else:
                                setattr(self, key, value)
        except Exception as e:
            print(f"加载 .env 文件失败: {e}")

    def save_config_to_env_file(self, config_data: Dict[str, Any]):
        """保存配置到 .env 文件"""
        try:
            # 读取现有的 .env 文件内容
            existing_lines = []
            existing_keys = set()

            if self.ENV_FILE_PATH.exists():
                with open(self.ENV_FILE_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        line_stripped = line.strip()
                        if (
                            line_stripped
                            and not line_stripped.startswith("#")
                            and "=" in line_stripped
                        ):
                            key = line_stripped.split("=", 1)[0].strip()
                            existing_keys.add(key)
                        existing_lines.append(line.rstrip())

            # 更新或添加新的配置项
            for key, value in config_data.items():
                env_line = f"{key}={value}"

                if key in existing_keys:
                    # 更新现有项
                    for i, line in enumerate(existing_lines):
                        if line.strip().startswith(f"{key}="):
                            existing_lines[i] = env_line
                            break
                else:
                    # 添加新项
                    existing_lines.append(env_line)

            # 保存到文件
            with open(self.ENV_FILE_PATH, "w", encoding="utf-8") as f:
                f.write("\n".join(existing_lines))
                if existing_lines and not existing_lines[-1] == "":
                    f.write("\n")

            print(f"配置已保存到: {self.ENV_FILE_PATH}")
        except Exception as e:
            print(f"保存 .env 配置文件失败: {e}")

    def get_saveable_config(self) -> Dict[str, Any]:
        """
        获取可保存的配置项（排除敏感信息）
        可以根据需要自定义哪些配置项不应该被保存
        """
        # 定义不应该保存到文件的敏感配置项
        sensitive_keys = {
            "TG_API_TOKEN",
            "PLEX_API_TOKEN",
            "OVERSEERR_API_TOKEN",
            "EMBY_API_TOKEN",
            "TAUTULLI_APIKEY",
            "REDIS_PASSWORD",
            "WEBAPP_SESSION_SECRET_KEY",
        }

        config = {}
        for key in dir(self):
            if (
                not key.startswith("_")
                and key.isupper()
                and key not in sensitive_keys
                and not callable(getattr(self, key))
            ):
                value = getattr(self, key)
                # 只保存基本类型
                if isinstance(value, (str, int, bool)):
                    config[key] = value
                if isinstance(value, list):
                    value = [str(v) for v in value]
                    config[key] = ",".join(value)

        return config

    def save_current_config(self, include_sensitive: bool = False):
        """
        保存当前配置到 .env 文件

        Args:
            include_sensitive: 是否包含敏感信息（如 API 密钥等）
        """
        if include_sensitive:
            # 保存所有配置项
            config = {}
            for key in dir(self):
                if (
                    not key.startswith("_")
                    and key.isupper()
                    and not callable(getattr(self, key))
                ):
                    value = getattr(self, key)
                    if isinstance(value, (str, int, bool)):
                        config[key] = value
                    if isinstance(value, list):
                        value = [str(v) for v in value]
                        config[key] = ",".join(value)
        else:
            # 只保存非敏感配置项
            config = self.get_saveable_config()

        self.save_config_to_env_file(config)

    class Config:
        case_sensitive = True
        # 支持从 .env 文件读取环境变量
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
