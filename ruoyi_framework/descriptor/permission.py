# -*- coding: utf-8 -*-
# @Author  : YY

from functools import wraps
from typing import Callable
from flask_login import UserMixin

from ruoyi_common.domain.entity import LoginUser
from ruoyi_common.utils import security_util as SecurityUtil
from ruoyi_common.utils.base import UtilException
from ruoyi_common.constant import HttpStatus


class PermissionService:
    """
    菜单权限
    """

    # 所有权限标识
    ALL_PERMISSION = "*:*:*"

    # 管理员角色权限标识
    SUPER_ADMIN = "admin"

    ROLE_DELIMETER = ","

    PERMISSION_DELIMETER = ","

    @classmethod
    def has_perm(cls, permission: str) -> bool:
        """
        验证用户是否具备某权限

        Args:
            permission (str): 权限标识

        Returns:
            bool: True:具备该权限，False:不具备该权限
        """
        if not permission:
            return False
        login_user: LoginUser = SecurityUtil.get_login_user()
        if not login_user:
            return False
        else:
            if not isinstance(login_user, UserMixin):
                return False
            user_authorities = login_user.permissions
            if not user_authorities: return False
        return cls.ALL_PERMISSION in user_authorities \
            or permission.strip() in user_authorities

    @classmethod
    def no_perm(cls, permission: str) -> bool:
        """
        验证用户是否不具备某权限

        Args:
            permission (str): 权限标识

        Returns:
            bool: True:不具备该权限，False:具备该权限
        """
        return not cls.has_perm(permission)

    @classmethod
    def any_perm(cls, permissions: str) -> bool:
        """
        验证用户是否具备某权限列表中的任意一个权限

        Args:
            permissions (str): 权限标识列表，多个权限标识以逗号分隔

        Returns:
            bool: True:具备任意一个权限，False:不具备任何一个权限
        """
        if not permissions: return False
        login_user: LoginUser = SecurityUtil.get_login_user()
        if not login_user:
            return False
        else:
            user_authorities = login_user.permissions
            if not user_authorities: return False
        for permission in permissions.split(cls.PERMISSION_DELIMETER):
            if cls.ALL_PERMISSION or permission.strip() in user_authorities:
                return True
        return False

    @classmethod
    def has_role(cls, role: str) -> bool:
        """
        验证用户是否具备某角色

        Args:
            role (str): 角色标识

        Returns:
            bool: True:具备该权限，False:不具备该权限
        """
        if not role:
            return False
        login_user: LoginUser = SecurityUtil.get_login_user()
        if not login_user or not login_user.user.roles:
            return False
        for sys_role in login_user.user.roles:
            if sys_role.role_key == cls.SUPER_ADMIN \
                    or sys_role.role_key == role.strip():
                return True
        return False

    @classmethod
    def no_role(cls, role: str) -> bool:
        """
        验证用户是否不具备某角色

        Args:
            role (str): 角色标识

        Returns:
            bool: True:具备该权限，False:不具备该权限
        """
        return not cls.has_role(role)

    @classmethod
    def any_role(cls, roles: str) -> bool:
        """
        验证用户是否具备某角色列表中的任意一个角色

        Args:
            roles (str): 角色标识列表，多个角色标识以逗号分隔

        Returns:
            bool: True:具备任意一个角色，False:不具备任何一个角色
        """
        if not roles: return False
        login_user: LoginUser = SecurityUtil.get_login_user()
        if not login_user or not login_user.user.roles:
            return False
        for role in roles.split(cls.ROLE_DELIMETER):
            for sys_role in login_user.user.roles:
                if sys_role.role_key == cls.SUPER_ADMIN \
                        or sys_role.role_key == role.strip():
                    return True
        return False


class AuthorityCaller:

    def __init__(self, value: str) -> None:
        self._value = value

    def __call__(self) -> bool:
        NotImplementedError()


def LoginRequired() -> bool:
    """

    验证用户是否登录

    Returns:
        bool -- True:已登录，False:未登录
    """
    login_user: LoginUser = SecurityUtil.get_login_user()
    if not login_user:
        return False
    if not login_user.is_authenticated:
        return False
    return True


class HasPerm(AuthorityCaller):
    """

    验证用户是否具备某权限

    """

    def __call__(self) -> bool:
        return PermissionService.has_perm(self._value)


class NoPerm(AuthorityCaller):
    """

    验证用户是否不具备某权限

    """

    def __call__(self) -> bool:
        return PermissionService.no_perm(self._value)


class AnyPerm(AuthorityCaller):
    """

    验证用户是否具备某权限列表中的任意一个权限

    """
    def __call__(self) -> bool:
        return PermissionService.any_perm(self._value)


class HasRole(AuthorityCaller):
    """

    验证用户是否具备某角色

    """

    def __call__(self) -> bool:
        return PermissionService.has_role(self._value)


class NoRole(AuthorityCaller):
    """

    验证用户是否不具备某角色

    """

    def __call__(self) -> bool:
        return PermissionService.no_role(self._role)


class AnyRole(AuthorityCaller):
    """

    验证用户是否具备某角色列表中的任意一个角色

    """

    def __call__(self) -> bool:
        return PermissionService.any_role(self._role)


class PreAuthorize:

    def __init__(self, auth: AuthorityCaller | Callable):
        self._auth = auth

    def __call__(self, func) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not callable(self._auth):
                raise UtilException("权限验证器必须是可调用对象", HttpStatus.ERROR)
            if not self._auth():
                raise UtilException("无访问权限", HttpStatus.FORBIDDEN)
            return func(*args, **kwargs)

        return wrapper
