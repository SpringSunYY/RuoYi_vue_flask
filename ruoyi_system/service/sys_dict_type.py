# -*- coding: utf-8 -*-
# @Author  : YY

from itertools import groupby
from types import NoneType
from typing import List, Optional
from flask import Flask
from pydantic_core import to_json, from_json

from ruoyi_common.constant import Constants, UserConstants
from ruoyi_common.base.signal import app_completed
from ruoyi_common.domain.entity import SysDictData, SysDictType
from ruoyi_common.sqlalchemy.transaction import Transactional
from ruoyi_common.exception import ServiceException
from ruoyi_system.mapper import SysDictDataMapper,SysDictTypeMapper
from ruoyi_admin.ext import redis_cache,db
from .. import reg


class SysDictTypeService:
    
    @classmethod
    def init(cls):
        '''
        初始化字典缓存
        '''
        cls.loading_dict_cache()
    
    @classmethod
    def loading_dict_cache(cls):
        '''
        加载字典缓存
        '''
        dict_data: SysDictData = SysDictData(status="0")
        dict_data_list = SysDictDataMapper.select_dict_data_list(dict_data)
        dict_data_list.sort(key=lambda x: x.dict_type)
        dict_data_map = groupby(dict_data_list, lambda x: x.dict_type)
        for key, group in dict_data_map:
            DictCacheUtil.set_dict_cache(key, list(group))
        
    @classmethod
    def clear_dict_cache(cls):
        '''
        清除字典缓存
        '''
        DictCacheUtil.clear_dict_cache()
    
    @classmethod
    def select_dict_data_by_type(cls, dict_type:str) -> List[SysDictData]:
        '''
        根据字典类型，查询字典数据列表
        
        Args:
            dict_type(str): 字典类型
        
        Returns:
            List[SysDictData]: 字典数据列表
        '''
        eos:List[SysDictData] = SysDictDataMapper.select_dict_data_by_type(dict_type)
        return eos
    
    @classmethod
    def select_dict_type_list(cls, dictype:SysDictType) -> List[SysDictType]:
        '''
        根据字典类型，查询字典类型列表
        
        Args:
            dictype(SysDictType): 字典类型
        
        Returns:
            List[SysDictType]: 字典类型列表
        '''
        eos:List[SysDictType] = SysDictTypeMapper.select_dict_type_list(dictype)
        return eos
    
    @classmethod
    def select_dict_type_all(cls) -> List[SysDictType]:
        '''
        所有字典类型
        
        Returns:
            List[SysDictType]: 字典类型列表
        '''
        eos:List[SysDictType] = SysDictTypeMapper.select_dict_type_all()
        return eos
    
    @classmethod
    def select_dict_type_by_id(cls, dict_id:int) -> SysDictType | NoneType:
        '''
        根据字典id，查询字典类型
        
        Args:
            dict_id(int): 字典id
        
        Returns:
            SysDictType | NoneType: 字典类型
        '''
        return SysDictTypeMapper.select_dict_type_by_id(dict_id)
    
    @classmethod
    def select_dict_type_by_type(cls, dict_type:str) -> SysDictType:
        '''
        根据字典类型，查询字典类型信息
        
        Args:
            dict_type(str): 字典类型
        
        Returns:
            SysDictType: 字典类型
        '''
        return SysDictTypeMapper.select_dict_type_by_type(dict_type)
    
    @classmethod
    def insert_dict_type(cls, dictype:SysDictType) -> bool:
        '''
        新增字典类型
        
        Args:
            dictype(SysDictType): 字典类型
        
        Returns:
            bool: 操作结果
        '''
        flag = SysDictTypeMapper.insert_dict_type(dictype)
        if flag and flag > 0:
            DictCacheUtil.set_dict_cache(dictype.dict_type, [])
        return True
    
    @classmethod
    @Transactional(db.session)
    def update_dict_type(cls, dictype:SysDictType) -> bool:
        '''
            修改字典类型
        '''
        old_dictype = SysDictTypeMapper.select_dict_type_by_id(
            dictype.dict_id
        )
        SysDictDataMapper.update_dict_data_type(
            old_dictype.dict_type, dictype.dict_type
        )
        num = SysDictTypeMapper.update_dict_type(dictype)
        flag = num > 0
        if flag:
            datas:List[SysDictData] = SysDictDataMapper \
                .select_dict_data_by_type(dictype.dict_type)
            DictCacheUtil.set_dict_cache(dictype.dict_type, datas)
        return flag 
    
    @classmethod
    @Transactional(db.session)
    def delete_dict_type_by_ids(cls, ids:List[int]) -> bool:
        '''
            批量删除字典类型
        '''
        for id in ids:
            dict_type = cls.select_dict_type_by_id(id)
            if dict_type is None:
                continue
            if SysDictDataMapper.select_dict_data_count_by_type(dict_type.dict_type) > 0:
                raise ServiceException("{}已分配,不能删除".format(dict_type.dict_type))
            SysDictTypeMapper.delete_dict_type_by_id(id)
            DictCacheUtil.remove_dict_cache(dict_type.dict_type)
        return True
    
    @classmethod
    def check_dict_type_unique(cls, dict_type:SysDictType):
        '''
            检查字典类型是否唯一
        '''
        eo:SysDictType = SysDictTypeMapper.check_dict_type_unique(dict_type.dict_type)
        if eo and dict_type.dict_id != eo.dict_id:
            return UserConstants.NOT_UNIQUE
        else:
            return UserConstants.UNIQUE
    
    @classmethod
    def reset_dict_type_cache(cls):
        '''
            重置字典缓存
        '''
        cls.clear_dict_cache()
        cls.loading_dict_cache()


class DictCacheUtil:
    
    @classmethod
    def clear_dict_cache(cls):
        pass
    
    @classmethod
    def get_cache_key(cls, key:str):
        return Constants.SYS_DICT_KEY + key
    
    @classmethod
    def remove_dict_cache(cls, key:str):
        redis_cache.delete(cls.get_cache_key(key))
    
    @classmethod
    def get_dict_value_sep(cls, dict_type, dict_label, sep):
        """
        根据字典类型和标签（支持分隔符），获取字典值
        
        Args:
            dict_type: 字典类型
            dict_label: 字典标签（支持分隔符分隔的多个标签）
            sep: 分隔符
            
        Returns:
            str: 字典值（多个值用分隔符连接）
        """
        if not dict_type or not dict_label:
            return dict_label
        labels = dict_label.split(sep) if sep else [dict_label]
        values = []
        for label in labels:
            value = cls.get_dict_value(dict_type, label.strip())
            if value:
                values.append(value)
            else:
                values.append(label.strip())
        return sep.join(values)
    
    @classmethod
    def get_dict_label_sep(cls, dict_type, dict_value, sep):
        """
        根据字典类型和值（支持分隔符），获取字典标签
        
        Args:
            dict_type: 字典类型
            dict_value: 字典值（支持分隔符分隔的多个值）
            sep: 分隔符
            
        Returns:
            str: 字典标签（多个标签用分隔符连接）
        """
        if not dict_type or not dict_value:
            return dict_value
        values = dict_value.split(sep) if sep else [dict_value]
        labels = []
        for value in values:
            label = cls.get_dict_label(dict_type, value.strip())
            if label:
                labels.append(label)
            else:
                labels.append(value.strip())
        return sep.join(labels)
    
    @classmethod
    def get_dict_value(cls, dict_type: str, dict_label: str) -> Optional[str]:
        """
        根据字典类型和标签，获取字典值
        
        Args:
            dict_type: 字典类型
            dict_label: 字典标签
            
        Returns:
            Optional[str]: 字典值，如果找不到则返回None
        """
        if not dict_type or not dict_label:
            return None
        dict_data_list = cls._get_dict_data_list(dict_type)
        if not dict_data_list:
            return None
        for dict_data in dict_data_list:
            if dict_data.dict_label == dict_label:
                return dict_data.dict_value
        return None
    
    @classmethod
    def get_dict_label(cls, dict_type: str, dict_value: str) -> Optional[str]:
        """
        根据字典类型和值，获取字典标签
        
        Args:
            dict_type: 字典类型
            dict_value: 字典值
            
        Returns:
            Optional[str]: 字典标签，如果找不到则返回None
        """
        if not dict_type or not dict_value:
            return None
        dict_data_list = cls._get_dict_data_list(dict_type)
        if not dict_data_list:
            return None
        for dict_data in dict_data_list:
            if dict_data.dict_value == str(dict_value):
                return dict_data.dict_label
        return None
    
    @classmethod
    def _get_dict_data_list(cls, dict_type: str) -> List[SysDictData]:
        """
        从缓存中获取字典数据列表
        
        Args:
            dict_type: 字典类型
            
        Returns:
            List[SysDictData]: 字典数据列表
        """
        try:
            cache_key = cls.get_cache_key(dict_type)
            cached_data = redis_cache.get(cache_key)
            if cached_data:
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode('utf-8')
                # 使用 from_json 解析列表，需要指定 List[SysDictData] 类型
                import json
                json_data = json.loads(cached_data)
                if isinstance(json_data, list):
                    dict_data_list = [SysDictData.model_validate(item) for item in json_data]
                else:
                    dict_data_list = [SysDictData.model_validate(json_data)] if json_data else []
                return dict_data_list
            # 如果缓存中没有，从数据库查询
            dict_data_list = SysDictDataMapper.select_dict_data_by_type(dict_type)
            if dict_data_list:
                cls.set_dict_cache(dict_type, dict_data_list)
            return dict_data_list
        except Exception:
            # 如果缓存读取失败，从数据库查询
            try:
                dict_data_list = SysDictDataMapper.select_dict_data_by_type(dict_type)
                return dict_data_list
            except Exception:
                return []
    
    @classmethod
    def set_dict_cache(cls, key, dict_data_list:List[SysDictData]):
        redis_cache.set(cls.get_cache_key(key), to_json(dict_data_list))


@app_completed.connect_via(reg.app)
def init(sender:Flask):
    '''
    初始化操作
    
    Args:
        sender (Flask): 消息发送者
    '''
    with sender.app_context():
        SysDictTypeService.init()

