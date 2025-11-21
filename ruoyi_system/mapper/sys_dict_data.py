# -*- coding: utf-8 -*-
# @Author  : YY

from typing import List, Optional
from flask import g
from sqlalchemy import and_, func
from sqlalchemy import delete, insert, select, update

from ruoyi_common.domain.entity import SysDictData
from ruoyi_common.sqlalchemy.model import ColumnEntityList
from ruoyi_common.sqlalchemy.transaction import Transactional
from ruoyi_system.domain.po import SysDictDataPo
from ruoyi_admin.ext import db


class SysDictDataMapper:

    """
    字典数据访问层
    """
    
    # 默认查询字段（接口返回字段）
    default_fields = {
        "dict_code",
        # 排序
        "dict_sort",
        "dict_label", "dict_type", "dict_value", "is_default",
        "status", "css_class", "list_class",
        # 审计字段
        "create_by", "create_time", "update_by", "update_time",
        # 备注
        "remark",
    }
    
    default_columns = ColumnEntityList(SysDictDataPo, default_fields, False)
 
    @classmethod
    def select_dict_data_list(cls, dictdata: Optional[SysDictData]) \
            -> List[SysDictData]:
        """
        根据条件，查询字典数据
        
        Args:
            dictdata (Optional[SysDictData]): 字典数据查询条件
        
        Returns:
            List[SysDictData]: 字典数据列表
        """
        criterions = []
        if dictdata:
            if dictdata.dict_type:
                criterions.append(
                    SysDictDataPo.dict_type == dictdata.dict_type
                )
            if dictdata.dict_label:
                criterions.append(
                    SysDictDataPo.dict_label.like(f'%{dictdata.dict_label}%')
                )
            if dictdata.status:
                criterions.append(SysDictDataPo.status == dictdata.status)
            stmt = select(*cls.default_columns) \
                .where(*criterions) \
                .order_by(SysDictDataPo.dict_sort.asc())
            if "page_criterian" in g:
                g.page_criterian[stmt] = dictdata.vo_obj
        else:
            stmt = select(*cls.default_columns) \
                .order_by(SysDictDataPo.dict_sort.asc())
        rows = db.session.execute(stmt).all()
        eos = list()
        for row in rows:
            eos.append(cls.default_columns.cast(row,SysDictData))
        return eos

    @classmethod
    def select_dict_data_by_type(cls, dict_type: str) -> List[SysDictData]:
        """
        根据字典类型，查询字典数据
        
        Args:
            dict_type (str): 字典类型
        
        Returns:
            List[SysDictData]: 字典数据列表    
        """
        stmt = select(*cls.default_columns) \
            .where(SysDictDataPo.dict_type == dict_type)
        rows = db.session.execute(stmt).all()
        eos = list()
        for row in rows:
            eos.append(cls.default_columns.cast(row,SysDictData))
        return eos

    @classmethod
    def select_dict_label(cls, dict_type: str, dict_value: str) -> Optional[str]:
        """
        根据字典类型和字典键值，查询字典标签
        
        Args:
            dict_type (str): 字典类型
            dict_value (str): 字典键值
        
        Returns:
            Optional[str]: 字典标签
        """
        stmt = select(SysDictDataPo.dict_label) \
            .where(and_(SysDictDataPo.dict_type == dict_type,
                        SysDictDataPo.dict_value == dict_value))
        return db.session.execute(stmt).scalar_one_or_none()

    @classmethod
    def select_dict_data_by_id(cls, dict_code: int) -> Optional[SysDictData]:
        """
        根据字典数据ID，查询字典数据信息
        
        Args:
            dict_code (int): 字典数据ID
        
        Returns:
            Optional[SysDictData]: 字典数据信息
        """
        stmt = select(*cls.default_columns) \
            .where(SysDictDataPo.dict_code == dict_code)
        row = db.session.execute(stmt).one_or_none()
        return cls.default_columns.cast(row, SysDictData) if row else None

    @classmethod
    def count_dict_data_by_type(cls, dict_type: str) -> int:
        """
        查询字典数据数量
        
        Args:
            dict_type (str): 字典类型
        
        Returns:
            int: 字典数据数量
        """
        stmt = select(func.count()).select_from(SysDictDataPo) \
            .where(SysDictDataPo.dict_type == dict_type)
        return db.session.execute(stmt).scalar_one()

    @classmethod
    @Transactional(db.session)
    def delete_dict_data_by_id(cls, dict_code: int) -> int:
        """
        通过字典ID，删除字典数据信息
        
        Args:
            dict_code (int): 字典ID
        
        Returns:
            int: 删除的行数
        """
        stmt = delete(SysDictDataPo) \
           .where(SysDictDataPo.dict_code == dict_code)
        return db.session.execute(stmt).rowcount

    @classmethod
    @Transactional(db.session)
    def delete_dict_data_by_ids(cls, dict_codes: List[int]) -> int:
        """
        批量删除字典数据信息
        
        Args:
            dict_codes (List[int]): 字典ID列表
        
        Returns:
            int: 删除的行数
        """
        stmt = delete(SysDictDataPo) \
           .where(SysDictDataPo.dict_code.in_(dict_codes))
        return db.session.execute(stmt).rowcount

    @classmethod
    @Transactional(db.session)
    def insert_dict_data(cls, dictdata: SysDictData) -> int:
        """
        新增字典数据信息
        
        Args:
            dictdata (SysDictData): 字典数据信息
        
        Returns:
            int: 新增记录的ID
        """
        fields = {
            "dict_type", "dict_label", "dict_value", "is_default", "status",
            "css_class", "list_class", "dict_sort", "create_by", "create_time",
            "remark"
        }
        data = dictdata.model_dump(
            include=fields,
            exclude_unset=True,
            exclude_none=True
        )
        stmt = insert(SysDictDataPo).values(data)
        out = db.session.execute(stmt).inserted_primary_key
        return out[0] if out else 0

    @classmethod
    @Transactional(db.session)
    def update_dict_data(cls, dictdata: SysDictData) -> int:
        """
        修改字典数据信息
        
        Args:
            dictdata (SysDictData): 字典数据信息
        
        Returns:
            int: 修改的行数
        """
        fields = {
            "dict_type", "dict_label", "dict_value", "is_default", "status",
            "css_class", "list_class", "dict_sort", "update_by", "update_time",
            "remark"
        }
        data = dictdata.model_dump(
            include=fields,
            exclude_unset=True,
            exclude_none=True
        )
        stmt = update(SysDictDataPo) \
            .where(SysDictDataPo.dict_code == dictdata.dict_code) \
            .values(data)
        return db.session.execute(stmt).rowcount

    @classmethod
    @Transactional(db.session)
    def update_dict_data_type(cls, old_dict_type: str, new_dict_type: str) -> int:
        """
        同步修改字典类型
        
        Args:
            old_dict_type (str): 旧字典类型
            new_dict_type (str): 新字典类型
        
        Returns:
            int: 修改的行数
        """
        stmt = update(SysDictDataPo).values(dict_type=new_dict_type) \
            .where(SysDictDataPo.dict_type == old_dict_type)
        return db.session.execute(stmt).rowcount
    
    @classmethod
    def select_dict_data_count_by_type(cls, dict_type: str) -> int:
        """
        查询字典数据数量
        
        Args:
            dict_type (str): 字典类型
        
        Returns:
            int: 字典数据数量
        """
        stmt = select(func.count()).select_from(SysDictDataPo) \
            .where(SysDictDataPo.dict_type == dict_type)
        return db.session.execute(stmt).scalar_one()
