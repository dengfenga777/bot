from pathlib import Path

from app.config import settings
from app.log import logger
from app.utils.utils import SingletonMeta
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class Scheduler(metaclass=SingletonMeta):
    def __init__(self) -> None:
        # 使用 SQLite 持久化任务存储，支持容器重启后恢复任务
        # 使用 Path 确保路径生成的健壮性
        if settings.DATA_DIR and settings.DATA_DIR.strip():
            db_path = Path(settings.DATA_DIR) / "scheduler.db"
        else:
            db_path = settings.DATA_PATH / "scheduler.db"
        
        # 确保目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"调度器数据库路径: {db_path}")

        self.jobstores = {
            "default": SQLAlchemyJobStore(url=f"sqlite:///{db_path}"),
        }
        self.executors = {
            "default": AsyncIOExecutor(),
            "threadpool": ThreadPoolExecutor(100),
        }
        self.scheduler = AsyncIOScheduler(
            jobstores=self.jobstores,
            executors=self.executors,
            timezone=settings.TZ,
            job_defaults={
                'coalesce': True,  # 将多个错过的任务合并为一个
                'max_instances': 1,  # 同一任务同时只能运行一个实例
            }
        )

        self.start()

    def start(self):
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()

    def add_jobstore(self, jobstore, alias, **kwargs):
        self.jobstores.update({alias: jobstore})
        self.scheduler.add_jobstore(jobstore, alias=alias, **kwargs)

    def add_job(self, *args, **kwargs):
        self.scheduler.add_job(*args, **kwargs)

    def add_async_job(self, func, *args, executor="default", **kwargs):
        """添加异步任务，默认使用AsyncIOExecutor"""
        return self.scheduler.add_job(func, *args, executor=executor, **kwargs)

    def add_sync_job(self, func, *args, executor="threadpool", **kwargs):
        """添加同步任务，使用ThreadPoolExecutor"""
        return self.scheduler.add_job(func, *args, executor=executor, **kwargs)

    def remove_job(self, job_id, jobstore=None):
        """移除任务"""
        self.scheduler.remove_job(job_id, jobstore=jobstore)

    def get_jobs(self, jobstore=None):
        """获取所有任务"""
        return self.scheduler.get_jobs(jobstore=jobstore)

    def pause_job(self, job_id, jobstore=None):
        """暂停任务"""
        self.scheduler.pause_job(job_id, jobstore=jobstore)

    def resume_job(self, job_id, jobstore=None):
        """恢复任务"""
        self.scheduler.resume_job(job_id, jobstore=jobstore)
