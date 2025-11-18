# -*- coding: utf-8 -*-
# @Author  : YY

import uuid
from datetime import datetime
from types import NoneType
from typing_extensions import Annotated
from flask_login import UserMixin
from pydantic import BaseModel, BeforeValidator, Field, Strict, computed_field
from typing import List, Optional
from pydantic.types import UUID4

from ruoyi_common.base.model import AuditEntity, VoAccess, strict_base_config
from ruoyi_common.base.schema_excel import ExcelAccess, ExcelField, ExcelFields
from ruoyi_common.base.schema_vo import VoField
from ruoyi_common.base.transformer import int_to_str, to_datetime, str_to_int


class LoginUser(BaseModel, UserMixin):
    model_config = strict_base_config.copy()

    user_id: int

    dept_id: Optional[int] = None

    token: UUID4 = Field(default_factory=uuid.uuid4)

    login_time: Annotated[
        datetime,
        BeforeValidator(to_datetime())
    ] = None

    expire_time: Annotated[
        datetime,
        BeforeValidator(to_datetime())
    ] = None

    ip_addr: Optional[str] = None

    login_location: Optional[str] = None

    browser: Optional[str] = None

    os: Optional[str] = None

    permissions: Optional[List] = []

    user: Optional["SysUser"] = None

    def get_id(self) -> int:
        return self.user_id

    @property
    def user_name(self) -> str:
        return self.user.user_name

    @property
    def dept_name(self) -> str:
        if self.user:
            if self.user.dept:
                return self.user.dept.dept_name
            else:
                return ""
        else:
            return ""


class SysUser(AuditEntity):
    user_id: Annotated[
        int,
        BeforeValidator(str_to_int),
        Field(gt=0, default=None),
        VoField(query=True),
        ExcelField(name="用户序号", cell_type="numeric", prompt="用户编号")
    ]

    dept_id: Annotated[
        Optional[int],
        BeforeValidator(str_to_int),
        Field(default=None),
        VoField(query=True),
        ExcelField(name="部门编号", action="import")
    ]

    user_name: Annotated[
        Optional[str],
        Field(default=None),
        VoField(query=True),
        ExcelField(name="登录名称")
    ]

    nick_name: Annotated[
        Optional[str],
        Field(default=None),
        ExcelField(name="用户名称")
    ]

    user_type: Optional[str] = None

    email: Annotated[
        Optional[str],
        Field(default=None),
        ExcelField(name="用户邮箱")
    ]

    phonenumber: Annotated[
        Optional[str],
        Field(default=None),
        VoField(query=True),
        ExcelField(name="手机号码")
    ]

    sex: Annotated[
        Optional[str],
        Field(default=None),
        ExcelField(name="用户性别", converter="0=男,1=女,2=未知")
    ]

    avatar: Optional[str] = None

    password: Annotated[
        str,
        Field(default=None, exclude=True)
    ]

    salt: Annotated[
        Optional[UUID4],
        Field(default=None),
        VoField(body=False)
    ]

    status: Annotated[
        Optional[str],
        Field(default=None),
        VoField(query=True),
        ExcelField(name="帐号状态", converter="0=正常,1=停用")
    ]

    del_flag: Optional[str] = None

    login_ip: Annotated[
        Optional[str],
        Field(default=None),
        ExcelField(name="最后登录IP", action="export")
    ]

    login_date: Annotated[
        Optional[datetime],
        BeforeValidator(to_datetime()),
        ExcelField(
            name="最后登录IP",
            width=30,
            date_format="yyyy-MM-dd HH:mm:ss",
            action="export"
        )
    ] = None

    dept: Annotated[
        "SysDept",
        Field(default=None),
        VoField(body=False),
        ExcelFields(
            ExcelAccess(name="部门名称", width=20, attr="dept_name"),
            ExcelAccess(name="部门负责人", width=20, attr="leader")
        )
    ]

    roles: Annotated[
        List["SysRole"],
        Field(default_factory=list),
        VoField(body=False)
    ]

    role_ids: Optional[List[int]] = []

    post_ids: Optional[List[int]] = []

    role_id: Annotated[
        Optional[int],
        Field(default=None),
        VoField(body=False)
    ]

    def is_admin(self) -> bool:
        return True if self.user_id and self.user_id == 1 else False


class SysRole(AuditEntity):
    role_id: Annotated[
        int,
        BeforeValidator(str_to_int),
        Field(gt=0, default=None, vo=VoAccess(query=True))
    ]

    role_name: Annotated[
        Optional[str],
        Field(default=None, vo=VoAccess(query=True))
    ]

    role_key: Annotated[
        Optional[str],
        Field(default=None, vo=VoAccess(query=True))
    ]

    role_sort: Annotated[
        Optional[int],
        BeforeValidator(str_to_int),
        Field(default=None)
    ]

    data_scope: Optional[str] = None

    menu_check_strictly: Annotated[Optional[bool], Strict(False)] = None

    dept_check_strictly: Annotated[Optional[bool], Strict(False)] = None

    status: Annotated[
        Optional[str],
        Field(default=None, vo=VoAccess(query=True))
    ]

    del_flag: Annotated[
        Optional[str],
        Field(default=None, vo=VoAccess(body=False))
    ]

    flag: Annotated[
        Optional[bool],
        Field(default=None, vo=VoAccess(body=False))
    ]

    menu_ids: Annotated[
        Optional[List[int]],
        Field(default=[], vo=VoAccess(body=False))
    ]

    dept_ids: Annotated[
        Optional[List[int]],
        Field(default=[], vo=VoAccess(body=False))
    ]

    def is_admin(self) -> bool:
        return self.role_id and self.role_id == 1 if self.role_id else False


class SysMenu(AuditEntity):
    menu_id: Annotated[
        int,
        BeforeValidator(str_to_int),
        Field(gt=0, default=None, vo=VoAccess(query=True))
    ]

    menu_name: Annotated[
        Optional[str],
        Field(default=None, vo=VoAccess(query=True))
    ]

    parent_name: Annotated[
        Optional[int],
        Field(default=None, exclude=True, vo=VoAccess(body=False))
    ]

    parent_id: Optional[int] = None

    order_num: Optional[int] = None

    path: Optional[str] = None

    component: Optional[str] = None

    query: Optional[str] = None

    is_frame: Annotated[str,
    BeforeValidator(int_to_str),
    Field(default=None)
    ]

    is_cache: Annotated[str,
    BeforeValidator(int_to_str),
    Field(default=None)
    ]

    menu_type: Optional[str] = None

    visible: Annotated[
        Optional[str],
        Field(default=None, vo=VoAccess(query=True))
    ]

    status: Annotated[
        Optional[str],
        Field(default=None, vo=VoAccess(query=True))
    ]

    perms: Optional[str] = None

    icon: Optional[str] = None

    children: Annotated[
        List["SysMenu"] | NoneType,
        Field(default=[], exclude=True, vo=VoAccess(body=False))
    ]


class SysDictType(AuditEntity):
    dict_id: Annotated[
        int,
        BeforeValidator(str_to_int),
        Field(default=None, ge=0, vo=VoAccess(query=True))
    ]

    dict_name: Annotated[
        str,
        Field(default=None, vo=VoAccess(query=True))
    ]

    dict_type: Annotated[
        str,
        Field(default=None, vo=VoAccess(query=True))
    ]

    status: Annotated[
        str,
        Field(default=None, vo=VoAccess(query=True))
    ]


class SysDictData(AuditEntity):
    dict_code: Annotated[
        int,
        BeforeValidator(str_to_int),
        Field(default=None, ge=0, vo=VoAccess(query=True))
    ]

    dict_sort: Annotated[int, Field(default=None)]

    dict_label: Annotated[
        str,
        Field(default=None, vo=VoAccess(query=True))
    ]

    dict_value: Annotated[
        str,
        Field(default=None, vo=VoAccess(query=True))
    ]

    dict_type: Annotated[
        str,
        Field(default=None, vo=VoAccess(query=True))
    ]

    css_class: Annotated[
        Optional[str],
        Field(default=None, vo=VoAccess(body=False))
    ]

    list_class: Annotated[
        str,
        Field(default=None)
    ]

    is_default: Annotated[str, Field(default=None)]

    status: Annotated[
        str,
        Field(default=None, vo=VoAccess(query=True))
    ]


class SysDept(AuditEntity):
    dept_id: Annotated[
        Optional[int],
        BeforeValidator(str_to_int),
        Field(default=None, vo=VoAccess(query=True))
    ]

    parent_id: Annotated[
        Optional[int],
        BeforeValidator(str_to_int),
        Field(default=None, vo=VoAccess(query=True))
    ]

    ancestors: Optional[str] = None

    dept_name: Annotated[
        Optional[str],
        Field(default=None, vo=VoAccess(query=True))
    ]

    order_num: Optional[int] = None

    leader: Optional[str] = None

    phone: Optional[str] = None

    email: Optional[str] = None

    status: Annotated[
        Optional[str],
        Field(default=None, vo=VoAccess(query=True))
    ]

    del_flag: Optional[str] = None

    parent_name: Annotated[Optional[str], Field(default=None, exclude=True, vo=VoAccess(body=False))]

    children: Annotated[List["SysDept"], Field(default=[], vo=VoAccess(body=False))]


class TreeSelect(BaseModel):
    # 节点ID
    id: Annotated[int, Field(default=None)]

    # 节点名称
    label: Annotated[str, Field(default=None)]

    # 子节点
    children: Annotated[List["TreeSelect"], Field(default=[])]

    @classmethod
    def from_menu(cls, menu: SysMenu) -> "TreeSelect":
        return cls(id=menu.menu_id, label=menu.menu_name, children=[cls.from_menu(child) for child in menu.children])

    @classmethod
    def from_dept(cls, dept: SysDept) -> "TreeSelect":
        return cls(id=dept.dept_id, label=dept.dept_name, children=[cls.from_dept(child) for child in dept.children])
