# -*- coding: utf-8 -*-
# @Author  : YY

from types import NoneType
from typing import List
from flask import Flask

from ruoyi_common.base.signal import app_completed
from ruoyi_common.utils import StringUtil
from ruoyi_common.constant import Constants, UserConstants
from ruoyi_common.exception import ServiceException
from ruoyi_system.mapper import SysConfigMapper
from ruoyi_system.domain.entity import SysConfig
from ruoyi_admin.ext import redis_cache
from .. import reg


class SysConfigService:

    @classmethod
    def init(cls):
        """
        初始化配置缓存
        """
        cls.loading_config_cache()

    @classmethod
    def select_config_by_id(cls, id: int) -> SysConfig|NoneType:
        """
        根据id查询配置信息

        Args:
            id (int): 配置ID

        Returns:
            SysConfig|NoneType: 配置信息
        """
        config = SysConfig(config_id=id)
        eo = SysConfigMapper.select_config(config)
        return eo

    @classmethod
    def select_config_by_key(cls, key: str) -> str|NoneType:
        """
        根据key查询配置值

        Args:
            key (str): 配置键

        Returns:
            str|NoneType: 配置值
        """
        config = SysConfig(config_key=key)
        value:bytes = redis_cache.get(cls.get_cache_key(key))
        if value:
            return value.decode("utf-8")
        eo = SysConfigMapper.select_config(config)
        if eo is None:
            return None
        redis_cache.set(cls.get_cache_key(key), eo.config_value.encode("utf-8"))
        return eo.config_value

    @classmethod
    def select_captcha_on_off(cls) -> bool:
        """
        查询验证码开关

        Returns:
            bool: 验证码开关
        """
        captcha_on_off = cls.select_config_by_key("sys.account.captchaOnOff")
        if captcha_on_off is None:
            return True
        return StringUtil.to_bool(captcha_on_off)

    @classmethod
    def select_config_list(cls, config: SysConfig|NoneType) -> List[SysConfig]:
        """
        查询配置列表

        Args:
            config (SysConfig|NoneType): 包含查询条件的传输对象

        Returns:
            List[SysConfig]: 配置列表
        """
        if config is not None:
            eos = SysConfigMapper.select_config_list(config)
        else:
            config = SysConfig()
            eos = SysConfigMapper.select_config_list(config)
        return eos

    @classmethod
    def insert_config(cls, config: SysConfig) -> bool:
        """
        新增配置

        Args:
            config (SysConfig): 新增配置信息

        Returns:
            bool: 新增成功返回True，否则返回False
        """
        flag = SysConfigMapper.insert_config(config)
        if flag and flag > 0:
            redis_cache.set(cls.get_cache_key(config.config_key), config.config_value.encode("utf-8"))
            return True
        return False

    @classmethod
    def update_config(cls, config: SysConfig) -> bool:
        """
        修改配置

        Args:
            config (SysConfig): 修改配置信息

        Returns:
            bool: 修改成功返回True，否则返回False
        """
        flag = SysConfigMapper.update_config(config)
        if flag and flag > 0:
            redis_cache.set(cls.get_cache_key(config.config_key), config.config_value.encode("utf-8"))
            return True
        return False

    @classmethod
    def delete_config_by_ids(cls, ids: List[int]) -> bool:
        """
        根据id删除配置

        Args:
            ids (List[int]): 配置ID列表

        Raises:
            bool: 删除成功返回True，否则返回False
        """
        deleting_ids = []
        for id in ids:
            config = cls.select_config_by_id(id)
            if not config:
                return
            if UserConstants.YES == config.config_type:
                raise ServiceException(f"Built-in parameter【{config.config_key}】cannot be deleted")
            redis_cache.delete(cls.get_cache_key(config.config_key))
            deleting_ids.append(id)
        flag = SysConfigMapper.delete_configs_by_ids(deleting_ids)
        return True if flag and flag > 0 else False

    @classmethod
    def loading_config_cache(cls):
        """
        加载配置缓存
        """
        configsList: List[SysConfig] = cls.select_config_list(None)
        for config in configsList:
            redis_cache.set(cls.get_cache_key(config.config_key), config.config_value)

    @classmethod
    def clear_config_cache(cls):
        """
        清除配置缓存
        """
        keys = redis_cache.keys(Constants.SYS_CONFIG_KEY + "*")
        redis_cache.delete(keys)

    @classmethod
    def reset_config_cache(cls):
        """
        重置配置缓存
        """
        cls.clear_config_cache()
        cls.loading_config_cache()

    @classmethod
    def check_config_key_unique(cls, body: SysConfig) -> str:
        """
        检查配置键是否唯一

        Args:
            body (SysConfig): 新增或修改配置信息

        Returns:
            str: 唯一返回UNIQUE，否则返回NOT_UNIQUE
        """
        exist = SysConfigMapper.check_config_key_unique(body.config_key)
        if exist and (body.config_id is None or exist.config_id != body.config_id):
            return UserConstants.NOT_UNIQUE
        return UserConstants.UNIQUE

    @classmethod
    def get_cache_key(cls, key: str) -> str:
        """
        获取缓存key

        Args:
            key (str): 配置键

        Returns:
            str: 缓存key
        """
        return Constants.SYS_CONFIG_KEY + key


@app_completed.connect_via(reg.app)
def init(sender:Flask):
    '''
    初始化操作

    Args:
        sender (Flask): 消息发送者
    '''
    with sender.app_context():
        SysConfigService.init()
