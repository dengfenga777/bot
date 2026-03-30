from typing import Optional

import redis
from app.config import settings
from app.log import logger


class Redis:
    def __init__(
        self,
        db: int = 0,
        host: str = settings.REDIS_HOST,
        port: int = settings.REDIS_PORT,
        password: str = settings.REDIS_PASSWORD,
        decode_responses: bool = True,
    ):
        self._pool = redis.ConnectionPool(
            db=db,
            host=host,
            port=port,
            password=password if password else None,
            decode_responses=decode_responses,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        self.client = redis.Redis(connection_pool=self._pool)

    def get_connection(self) -> redis.Redis:
        """获取Redis连接"""
        return self.client

    def get_pool(self) -> redis.ConnectionPool:
        """获取连接池"""
        return self._pool

    def close(self) -> None:
        """关闭连接池，释放所有连接"""
        try:
            self._pool.disconnect()
            logger.info("Redis连接池已关闭")
        except Exception as e:
            logger.error(f"关闭Redis连接池时出错: {e}")

    def health_check(self) -> bool:
        """检查Redis连接是否健康"""
        try:
            return self.client.ping()
        except redis.ConnectionError as e:
            logger.error(f"Redis连接检查失败: {e}")
            return False
        except redis.TimeoutError as e:
            logger.error(f"Redis连接超时: {e}")
            return False
        except Exception as e:
            logger.error(f"Redis健康检查异常: {e}")
            return False

    def get_info(self) -> Optional[dict]:
        """获取Redis服务器信息"""
        try:
            return self.client.info()
        except Exception as e:
            logger.error(f"获取Redis信息失败: {e}")
            return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
