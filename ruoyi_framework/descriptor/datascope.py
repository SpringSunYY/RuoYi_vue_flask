# -*- coding: utf-8 -*-
# @Author  : YY

from enum import Enum
from functools import wraps
from typing import Any, Literal
from flask import g
from pydantic import ConfigDict, Field, validate_call
from pydantic.dataclasses import dataclass
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql.expression import or_
from sqlalchemy import func

from ruoyi_common.base.model import CriterianMeta
from ruoyi_common.descriptor.validator import ValidatorScopeFunction
from ruoyi_common.base.schema_vo import BaseEntity
from ruoyi_common.domain.entity import LoginUser, SysUser
from ruoyi_common.utils import security_util as SecurityUtil
from ruoyi_system.domain.po import SysDeptPo, SysRoleDeptPo, SysUserPo


class DataScopeEnum(Enum):
    ALL = "1"

    CUSTOM = "2"

    DEPT = "3"

    DEPT_AND_CHILD = "4"

    SELF = "5"


@dataclass
class DataScope:
    """
    数据权限范围
    """
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        populate_by_name=True
    )

    # DATA_SCOPE: Literal["data_scope"] = Field(init=False, exclude=True, repr=False)

    dept: bool = True
    user: bool = False
    user_field: str = "user_id"

    def __call__(self, func) -> Any:

        vsfunc = ValidatorScopeFunction(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            unbound_model = vsfunc.unbound_model
            if unbound_model:
                key, _ = unbound_model
                # 首先尝试从关键字参数获取
                bo = kwargs.get(key)
                if bo is None:
                    # 如果关键字参数中没有，尝试从位置参数获取
                    param_names = list(vsfunc.sig.parameters.keys())
                    if key in param_names:
                        param_index = param_names.index(key)
                        if param_index < len(args):
                            bo = args[param_index]
                self.handle_data_scope(bo)
            else:
                print("没有找到unbound_model")
            return vsfunc(*args, **kwargs)

        return wrapper

    def handle_data_scope(self, bo: BaseEntity):
        """
        处理数据权限范围

        Args:
            bo (BaseEntity): 校验对象
        """
        login_user: LoginUser = SecurityUtil.get_login_user()
        if login_user:
            current_user: SysUser = login_user.user
            # 检查用户是否为超级管理员（用户ID为1或者具有admin角色）
            if not SecurityUtil.is_admin(login_user.user_id) and not self.is_user_admin(current_user):
                self.filter_data_scope(bo, current_user)

    def is_user_admin(self, user: SysUser) -> bool:
        """
        判断用户是否为管理员（通过角色判断）

        Args:
            user (SysUser): 用户对象

        Returns:
            bool: 是否为管理员
        """
        return SecurityUtil.is_user_admin(user)

    def filter_data_scope(self, bo: BaseEntity, user: SysUser):
        """
        过滤数据权限范围

        Args:
            bo (BaseEntity): 校验对象
            user (SysUser): 当前用户
        """
        criterian_meta: CriterianMeta = g.criterian_meta
        criterions = []
        for role in user.roles:
            if role.data_scope == DataScopeEnum.ALL.value:
                # 全部数据权限
                criterions = []
                break
            elif role.data_scope == DataScopeEnum.CUSTOM.value:
                # 自定义数据权限
                subquery = SysRoleDeptPo.query(SysRoleDeptPo.dept_id) \
                    .filter(
                    SysRoleDeptPo.role_id == role.role_id
                ).subquery()
                if self.dept is True:
                    criterion = SysDeptPo.dept_id.in_(subquery)
                elif isinstance(self.dept, AliasedClass):
                    criterion = self.dept.dept_id.in_(subquery)
                if criterion:
                    criterions.append(criterion)
            elif role.data_scope == DataScopeEnum.DEPT.value:
                # 本部门数据权限
                if self.dept is True:
                    criterion = SysDeptPo.dept_id == user.dept_id
                elif isinstance(self.dept, AliasedClass):
                    criterion = self.dept.dept_id == user.dept_id
                if criterion:
                    criterions.append(criterion)
            elif role.data_scope == DataScopeEnum.DEPT_AND_CHILD.value:
                # 本部门及子部门数据权限
                subquery = SysDeptPo.query(SysDeptPo.dept_id) \
                    .filter(
                    or_(
                        SysDeptPo.dept_id == user.dept_id,
                        func.find_in_set(user.dept_id, SysDeptPo.ancestors)
                    )
                ).subquery()
                if self.dept is True:
                    criterion = SysDeptPo.dept_id.in_(subquery)
                elif isinstance(self.dept, AliasedClass):
                    criterion = self.dept.dept_id.in_(subquery)
                if criterion:
                    criterions.append(criterion)
            elif role.data_scope == DataScopeEnum.SELF.value:
                # 仅本人数据权限
                if self.user is True:
                    # 根据业务对象类型动态确定要过滤的字段
                    criterion = self._get_user_filter_criterion(bo, user)
                    if criterion is not None:
                        criterions.append(criterion)
                elif isinstance(self.user, AliasedClass):
                    criterion = self.user.user_id == user.user_id
                    criterions.append(criterion)
                else:
                    criterion = "1=0"
                    criterions.append(criterion)
            else:
                print(ValueError("Invalid data_scope value: {}".format(role.data_scope)))

        if criterions:
            data_scope = or_(*criterions)
        else:
            data_scope = None

        criterian_meta.scope = data_scope

    def _get_user_filter_criterion(self, bo: BaseEntity, user: SysUser):
        """
        根据业务对象类型获取用户过滤条件

        Args:
            bo (BaseEntity): 业务对象
            user (SysUser): 当前用户

        Returns:
            过滤条件
        """
        # 根据业务对象模块确定 PO 类位置
        bo_module = bo.__class__.__module__
        bo_class_name = bo.__class__.__name__

        # 使用通用规则
        po_module_path = bo_module.replace('.entity.', '.po.') + '_po'
        po_class_name = bo_class_name + 'Po'

        try:
            # 动态导入 PO 模块
            po_module = __import__(po_module_path, fromlist=[po_class_name])
            po_class = getattr(po_module, po_class_name)

            # 获取用户字段
            user_field = getattr(po_class, self.user_field, None)
            if user_field is not None:
                return user_field == user.user_id
            else:
                # 如果没有找到用户字段，不添加过滤条件
                print(f"DataScope: 在 {po_class} 中找不到用户字段 {self.user_field}")
                return None
        except (ImportError, AttributeError) as e:
            print(f"DataScope: 无法找到对应的 PO 类 {po_module_path}.{po_class_name}: {e}")
            # 如果找不到对应的 PO 类，不添加过滤条件
            return None
