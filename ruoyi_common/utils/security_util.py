# -*- coding: utf-8 -*-
# @Author  : YY

import bcrypt
from flask import abort
from flask_login import current_user
from ruoyi_common.constant import HttpStatus
from ruoyi_common.domain.entity import LoginUser
from ruoyi_common.utils.base import UtilException


def get_user_id() -> int:
    """
    获取当前登录用户的ID

    Raises:
        UtilException: 获取用户ID异常

    Returns:
        int: 当前登录用户的ID 
    """
    try:
        return get_login_user().user_id
    except Exception:
        raise UtilException("获取用户ID异常", HttpStatus.UNAUTHORIZED)

def get_dept_id() -> int:
    """
    获取当前登录用户的部门ID

    Raises:
        UtilException: 获取部门ID异常

    Returns:
        int: 当前登录用户的部门ID 
    """
    try:
        return get_login_user().dept_id
    except Exception:
        raise UtilException("获取部门ID异常", HttpStatus.UNAUTHORIZED)

def get_username() -> str:
    """
    获取当前登录用户的账户

    Raises:
        UtilException: 获取用户账户异常

    Returns:
        str: 当前登录用户的账户 
    """
    try:
        return get_login_user().user_name
    except Exception as e:
        raise UtilException("获取用户账户异常", HttpStatus.UNAUTHORIZED)

def get_login_user() -> LoginUser:
    """
    获取当前登录用户的信息

    Raises:
        UtilException: 获取用户信息异常

    Returns:
        LoginUser: 当前登录用户的信息 
    """
    try:
        # 检查是否有Flask-Login支持
        if hasattr(current_user, 'is_authenticated'):
            if not current_user.is_authenticated:
                abort(401)
            return current_user
        else:
            # 如果没有Flask-Login支持，返回None或抛出异常
            raise UtilException("获取用户信息异常", HttpStatus.UNAUTHORIZED)
    except Exception:
        raise UtilException("获取用户信息异常", HttpStatus.UNAUTHORIZED)

def is_admin(user_id) -> bool:
    """
    判断用户是否为管理员

    Args:
        user_id (int): 用户ID

    Returns:
        bool: 用户是否为管理员
    """
    return user_id is not None and user_id == 1

def is_user_admin(user) -> bool:
    """
    通过用户对象判断是否为管理员
    
    Args:
        user: 用户对象
        
    Returns:
        bool: 是否为管理员
    """
    # 检查是否为超级管理员用户
    if is_admin(user.user_id):
        return True
    
    # 检查用户角色中是否包含admin角色
    if hasattr(user, 'roles') and user.roles:
        for role in user.roles:
            if hasattr(role, 'role_key') and role.role_key == 'admin':
                return True
    return False

def login_user_is_admin() -> bool:
    """
    判断当前登录用户是否为管理员

    Returns:
        bool: 当前登录用户是否为管理员
    """
    try:
        user = get_login_user().user
        return is_user_admin(user)
    except:
        return is_admin(get_user_id())


def encrypt_password(password: str) -> str:
    """
    使用 bcrypt 加密密码
    """
    if not password:
        raise UtilException("密码不能为空", HttpStatus.BAD_REQUEST)
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def matches_password(raw_password: str, encoded_password: str) -> bool:
    """
    判断原始密码与加密密码是否匹配
    """
    if not raw_password or not encoded_password:
        return False
    try:
        return bcrypt.checkpw(
            raw_password.encode("utf-8"),
            encoded_password.encode("utf-8"),
        )
    except ValueError:
        # encoded_password 不是合法的 bcrypt 字符串
        return False