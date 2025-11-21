# -*- coding: utf-8 -*-
# @Author  : YY

from typing import List, Optional
from flask import g
from sqlalchemy import delete, insert, select, update

from ruoyi_common.domain.entity import SysDictType
from ruoyi_common.sqlalchemy.model import ColumnEntityList
from ruoyi_common.sqlalchemy.transaction import Transactional
from ruoyi_system.domain.po import SysDictTypePo
from ruoyi_admin.ext import db


class SysDictTypeMapper:

    """
    字典类型访问层
    """
    
    # 默认查询字段（接口返回字段）
    default_fields = {
        "dict_id", "dict_name", "dict_type", "status",
        # 审计字段
        "create_by", "create_time", "update_by", "update_time",
        # 备注
        "remark",
    }
    
    default_columns = ColumnEntityList(SysDictTypePo, default_fields, False)
    
    @classmethod
    def select_dict_type_list(cls, dictype: Optional[SysDictType]) \
        -> List[SysDictType]:
        """
        根据条件，查询字典类型
        
        Args:
            dictype (Optional[SysDictType]): 查询条件
        
        Returns:
            List[SysDictType]: 字典类型列表
        """
        if dictype:
            criterions = []
            if dictype.dict_type:
                criterions.append(
                   SysDictTypePo.dict_type.like(f'%{dictype.dict_type}%')
                )
            if dictype.dict_name:
                criterions.append(
                    SysDictTypePo.dict_name.like(f'%{dictype.dict_name}%')
                )
            if dictype.status:
                criterions.append(
                    SysDictTypePo.status == dictype.status
                ) 
            
            stmt = select(*cls.default_columns) \
                .where(*criterions)
            if "criterian_meta" in g and g.criterian_meta.page:
                g.criterian_meta.page.stmt = stmt
        else:
            stmt = select(*cls.default_columns)
        
        rows = db.session.execute(stmt).all()
        eos = list()
        for row in rows:
            eos.append(cls.default_columns.cast(row,SysDictType))
        return eos

    @classmethod
    def select_dict_type_all(cls) -> List[SysDictType]:
        """
        查询所有字典类型
        
        Args:
            None
        
        Returns:
            List[SysDictType]: 字典类型列表
        """
        return cls.select_dict_type_list(None)

    @classmethod
    def select_dict_type_by_id(cls, dict_id: int) -> Optional[SysDictType]:
        """
        根据字典类型ID，查询信息
        
        Args:
            dict_id (int): 字典类型ID
        
        Returns:
            Optional[SysDictType]: 字典类型信息
        """
        stmt = select(*cls.default_columns) \
            .where(SysDictTypePo.dict_id == dict_id)
        row = db.session.execute(stmt).first()
        return cls.default_columns.cast(row,SysDictType) if row else None

    @classmethod
    def select_dict_type_by_type(cls, dict_type: str) -> Optional[SysDictType]:
        """
        根据字典类型，查询字典类型信息
        
        Args:
            dict_type (str): 字典类型
        
        Returns:
            Optional[SysDictType]: 字典类型信息
        """
        stmt = select(*cls.default_columns) \
            .where(SysDictTypePo.dict_type == dict_type)
        row = db.session.execute(stmt).first()
        return cls.default_columns.cast(row,SysDictType) if row else None
    
    @classmethod
    @Transactional(db.session)
    def delete_dict_type_by_id(cls, dict_id: int) -> int:
        """
        通过字典ID，删除字典信息
        
        Args:
            dict_id (int): 字典ID
        
        Returns:
            int: 删除的行数
        """
        stmt = delete(SysDictTypePo) \
            .where(SysDictTypePo.dict_id == dict_id)
        return db.session.execute(stmt).rowcount
            
    @classmethod
    @Transactional(db.session)
    def delete_dict_type_by_ids(cls, dict_ids: List[int]) -> int:
        """
        批量删除字典类型信息
        
        Args:
            dict_ids (List[int]): 字典ID列表
        
        Returns:
            int: 删除的行数
        """
        stmt = delete(SysDictTypePo) \
            .where(SysDictTypePo.dict_id.in_(dict_ids))
        return db.session.execute(stmt).rowcount

    @classmethod
    @Transactional(db.session)
    def insert_dict_type(cls, dictype: SysDictType) -> int:
        """
        新增字典类型信息
        
        Args:
            dictype (SysDictType): 字典类型信息
        
        Returns:
            int: 新增记录的ID
        """
        fields = {
            "dict_name","dict_type","status","create_by","create_time","remark"
        }
        data = dictype.model_dump(
            include=fields,include_none=True,exclude_unset=True
        )
        stmt = insert(SysDictTypePo).values(data)
        out = db.session.execute(stmt).inserted_primary_key
        return out[0] if out else 0

    @classmethod
    @Transactional(db.session)
    def update_dict_type(cls, dict_type: SysDictType) -> int:
        """
        修改字典类型信息
        
        Args:
            dict_type (SysDictType): 字典类型信息
        
        Returns:
            int: 修改的行数
        """
        fields = {
            "dict_name","dict_type","status","update_by","update_time","remark"
        }
        data = dict_type.model_dump(
            include=fields,exclude_none=True,exclude_unset=True
        )
        stmt = update(SysDictTypePo) \
            .where(SysDictTypePo.dict_id == dict_type.dict_id) \
            .values(data)
        return db.session.execute(stmt).rowcount

    @classmethod
    def check_dict_type_unique(cls, dict_type: str) -> Optional[SysDictType]:
        """
        校验字典类型是否唯一
        
        Args:
            dict_type (str): 字典类型
        
        Returns:
            Optional[SysDictType]: 字典类型信息
        """
        stmt = select(*cls.default_columns) \
            .where(SysDictTypePo.dict_type == dict_type) \
            .limit(1)
        row = db.session.execute(stmt).one_or_none()
        return cls.default_columns.cast(row,SysDictType) if row else None
