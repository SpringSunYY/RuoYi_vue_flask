# -*- coding: utf-8 -*-
# @Author  : YY

import atexit
from datetime import datetime
from typing import List, Optional
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, \
    EVENT_JOB_MISSED, EVENT_JOB_SUBMITTED, EVENT_JOB_REMOVED, JobEvent
from flask import Flask
import importlib

from ruoyi_common.base.signal import app_completed
from ruoyi_common.exception import ServiceException
from ruoyi_common.sqlalchemy.transaction import Transactional
from ruoyi_apscheduler.constant import ScheduleStatus
from ruoyi_apscheduler.domain.entity import SysJob, SysJobLog
from ruoyi_apscheduler.mapper.job import SysJobMapper
from ruoyi_apscheduler.util import ScheduleUtil, check_method_importable
from ruoyi_apscheduler.service.job_log import SysJobLogService
from ruoyi_admin.ext import db
from .. import reg, scheduler


class SysJobService:

    @classmethod
    def init(cls):
        """
        初始化定时任务
        """
        scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | \
                               EVENT_JOB_ERROR | EVENT_JOB_MISSED | EVENT_JOB_SUBMITTED | \
                               EVENT_JOB_REMOVED)

        scheduler.remove_all_jobs()
        try:
            for job in SysJobMapper.select_job_all():
                ScheduleUtil.create_schedule_job(scheduler, job)
        except ImportError as e:
            raise ServiceException(f"导入定时任务失败，请检查表SysJob的数据：{e}")

        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())

    @classmethod
    def select_job_list(cls, job: SysJob) -> List[SysJob]:
        """
        查询定时任务列表

        Args:
            job (SysJob): 包含查询条件的任务

        Returns:
            List[SysJob]: 任务信息列表
        """
        return SysJobMapper.select_job_list(job)

    @classmethod
    def select_job_by_id(cls, job_id: int) -> Optional[SysJob]:
        """
        查询定时任务

        Args:
            job_id (int): 任务ID

        Returns:
            Optional[SysJob]: 任务信息
        """
        return SysJobMapper.select_job_by_id(job_id)

    @classmethod
    @Transactional(db.session)
    def insert_job(cls, job: SysJob) -> bool:
        """
        新增定时任务

        Args:
            job (SysJob): 任务信息

        Returns:
            bool: 操作结果
        """
        flag = SysJobMapper.insert_job(job)
        if flag:
            ScheduleUtil.create_schedule_job(scheduler, job)
        return flag > 0

    @classmethod
    @Transactional(db.session)
    def update_job(cls, job: SysJob) -> bool:
        """
        更新定时任务

        Args:
            job (SysJob): 任务信息

        Returns:
            bool: 操作结果
        """
        db_job: SysJob = cls.select_job_by_id(job.job_id)
        flag = SysJobMapper.update_job(job)
        if flag > 0:
            sched_job = scheduler.get_job(db_job.job_key)
            if sched_job:
                scheduler.remove_job(db_job.job_key)
            ScheduleUtil.create_schedule_job(scheduler, job)
        return flag > 0

    @classmethod
    @Transactional(db.session)
    def delete_job_by_id(cls, job: SysJob) -> int:
        """
        删除定时任务

        Args:
            job (SysJob): 任务信息

        Returns:
            int: 删除的任务数量
        """
        num = SysJobMapper.delete_job_by_id(job.job_id)
        if num > 0:
            scheduler.remove_job(job.job_key)
        return num

    @classmethod
    @Transactional(db.session)
    def delete_job_by_ids(cls, job_ids: List[int]):
        """
        批量删除定时任务

        Args:
            job_ids (List[int]): 任务ID列表
        """
        for job_id in job_ids:
            job = cls.select_job_by_id(job_id)
            if job:
                cls.delete_job_by_id(job)

    @classmethod
    @Transactional(db.session)
    def pause_job(cls, job: SysJob) -> int:
        """
        暂停定时任务

        Args:
            job (SysJob): 任务信息

        Returns:
            int: 操作结果
        """
        job.status = ScheduleStatus.PAUSED.value
        num = SysJobMapper.update_job(job)
        if num > 0:
            scheduler.pause_job(job.job_key)
        return num

    @classmethod
    @Transactional(db.session)
    def resume_job(cls, job: SysJob) -> int:
        """
        恢复定时任务

        Args:
            job (SysJob): 任务信息

        Returns:
            int: 操作结果
        """
        job.status = ScheduleStatus.NORMAL.value
        num = SysJobMapper.update_job(job)
        if num > 0:
            sched_job = scheduler.get_job(job.job_key)
            if not sched_job:
                # APScheduler 中不存在该任务时重新创建
                ScheduleUtil.create_schedule_job(scheduler, job)
            else:
                scheduler.resume_job(job.job_key)
        return num

    @classmethod
    @Transactional(db.session)
    def change_job_status(cls, job: SysJob) -> int:
        """
        更改定时任务状态

        Args:
            job (SysJob): 任务信息

        Returns:
            int: 操作结果
        """
        num = 0
        if job.status == ScheduleStatus.NORMAL.value:
            num = cls.resume_job(job)
        elif job.status == ScheduleStatus.PAUSED.value:
            num = cls.pause_job(job)
        return num

    @classmethod
    def run(cls, job: SysJob):
        """
        立即执行定时任务

        Args:
            job (SysJob): 任务信息
        """
        # 先从数据库取全量信息，避免缺失 job_group 等导致 job_key 不匹配
        db_job = cls.select_job_by_id(job.job_id)
        if not db_job:
            raise ServiceException("任务不存在")
        print(f"[job_run] 请求立即执行，job_key={db_job.job_key}, invoke_target={db_job.invoke_target}")

        # 直接调用目标函数，确保“执行一次”必定执行
        module_name, method_name, args, kwargs = ScheduleUtil.parse_target(db_job.invoke_target)
        if not check_method_importable(module_name, method_name):
            raise ServiceException(f"方法不存在: {db_job.invoke_target}")
        func = getattr(importlib.import_module(module_name), method_name)
        try:
            func(*args, **kwargs)
        except Exception as e:
            raise ServiceException(f"立即执行任务失败: {e}")

        # 维持调度器中的任务（下一次仍按 cron 跑）
        sched_job = scheduler.get_job(db_job.job_key)
        if sched_job is None:
            ScheduleUtil.create_schedule_job(scheduler, db_job)


def job_listener(event: JobEvent):
    """
    任务监听器

    Args:
        event (JobEvent): 任务事件
    """
    job, _ = scheduler._lookup_job(event.job_id, event.jobstore)
    job_state = job.__getstate__()
    invoke_target = ScheduleUtil.unparse_target_by_funcname(
        job_state["func"],
        job_state["args"],
        job_state["kwargs"]
    )
    name = job_state["name"]
    _, group = job_state["id"].split("_")

    joblog = SysJobLog(
        job_name=name,
        job_group=group,
        invoke_target=invoke_target,
        create_time=datetime.now()
    )

    if event.code == EVENT_JOB_EXECUTED:
        pass
    elif event.code == EVENT_JOB_ERROR:
        if event.exception:
            joblog.status = "1"
            joblog.exception_info = str(event.exception)
            joblog.job_message = str(event.traceback)
            print(f"任务{event.job_id}异常：{event.exception}")
    elif event.code == EVENT_JOB_MISSED:
        pass
    elif event.code == EVENT_JOB_SUBMITTED:
        pass
    elif event.code == EVENT_JOB_REMOVED:
        pass
    with reg.app.app_context():
        SysJobLogService.insert_job_log(joblog)


@app_completed.connect_via(reg.app)
def init(sender: Flask):
    '''
    初始化操作

    Args:
        sender (Flask): 消息发送者
    '''
    with sender.app_context():
        SysJobService.init()
