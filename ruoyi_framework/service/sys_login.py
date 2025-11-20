# -*- coding: utf-8 -*-

import datetime
from flask import  Request, request

from ruoyi_common.constant import Constants
from ruoyi_common.domain.vo import LoginBody
from ruoyi_common.utils import AddressUtil, IpUtil, MessageUtil
from ruoyi_common.utils import security_util as SecurityUtil
from ruoyi_common.domain.entity import LoginUser, SysUser
from ruoyi_common.domain.enum import UserStatus
from ruoyi_common.exception import ServiceException
from ruoyi_common.utils.base import UserAgentUtil
from ruoyi_framework.asyncsched.manager import TaskManager
from ruoyi_framework.asyncsched.task import record_logininfor
from ruoyi_system.domain.entity import SysLogininfor
from ruoyi_system.service import SysConfigService,SysUserService
from ruoyi_system.service.sys_post import SysPostService
from ruoyi_admin.ext import lm,redis_cache
from .token import TokenService
from .sys_permission import SysPermissionService


class LoginService:
    
    @classmethod
    def login(cls, login: LoginBody) -> str:
        """
        登录

        Args:
            login (LoginBody): 登录参数

        Raises:
            ServiceException: 登录失败
            ServiceException: 验证码错误

        Returns:
            str: 登录token
        """
        captcha_on_off = SysConfigService.select_captcha_on_off()
        if captcha_on_off:
            cls.validate_captcha(login.username, login.code, login.uuid)
        sysuser = SysUserService.select_user_by_user_name(login.username)
        if not sysuser:
            logininfor = cls.build_logininfor(
                login.username, 
                Constants.LOGIN_FAIL, 
                MessageUtil.message(code="user.password.not.match")
            )
            TaskManager.execute(record_logininfor,logininfor)
            raise ServiceException(f"登录用户：{login.username} 不存在")
        if not SecurityUtil.matches_password(login.password.get_secret_value(), sysuser.password):
            logininfor = cls.build_logininfor(
                login.username, 
                Constants.LOGIN_FAIL, 
                MessageUtil.message(code="user.password.not.match")
            )
            TaskManager.execute(record_logininfor,logininfor)
            raise ServiceException("用户名或密码不匹配")
        logininfor = cls.build_logininfor(
            login.username, 
            Constants.LOGIN_SUCCESS, 
            MessageUtil.message(code="user.login.success")
        )
        TaskManager.execute(record_logininfor,logininfor)
        login_user = cls.load_user(sysuser)
        cls.record_sysuser(login_user.user_id)
        return TokenService.create_token(login_user)
    
    @classmethod
    def load_user(cls, user:SysUser) -> LoginUser:
        """
        加载登录用户

        Args:
            user (SysUser): 用户信息

        Raises:
            ServiceException: 用户已删除
            ServiceException: 用户已停用

        Returns:
            LoginUser: 登录用户
        """
        if user.del_flag == UserStatus.DELETED.value:
            raise ServiceException(f"对不起，您的账号：{user.user_name} 已删除")
        if user.status == UserStatus.DISABLE.value:
            raise ServiceException(f"对不起，您的账号：{user.user_name} 已停用")
        if not user.role_ids:
            dedup_role_ids = []
            seen_role_ids = set()
            for role in user.roles:
                role_id = getattr(role, "role_id", None)
                if role_id and role_id not in seen_role_ids:
                    seen_role_ids.add(role_id)
                    dedup_role_ids.append(role_id)
            user.role_ids = dedup_role_ids
        if not user.role_id and user.role_ids:
            user.role_id = user.role_ids[0]
        if not user.post_ids:
            user.post_ids = SysPostService.select_post_list_by_user_id(user.user_id)
        login_user = LoginUser(
            user_id=user.user_id,
            dept_id=user.dept_id,
            permissions=SysPermissionService.get_menu_permission(user),
            user=user,
        )
        return login_user

    @classmethod
    def validate_captcha(cls, username:str, code:str, uuid:str):
        """
        验证码校验

        Args:
            username (str): 用户名
            code (str): 验证码
            uuid (str): 验证码唯一标识

        Raises:
            ServiceException: 验证码无效
            ServiceException: 验证码过期
        """
        verify_key = Constants.CAPTCHA_CODE_KEY + str(uuid)
        captcha:bytes = redis_cache.get(verify_key)
        if not captcha:
            logininfor = cls.build_logininfor(
                username, 
                Constants.LOGIN_FAIL, 
                MessageUtil.message("user.jcaptcha.expire")
            )
            TaskManager.execute(record_logininfor,logininfor)
            raise ServiceException("验证码无效")
        redis_cache.delete(verify_key)
        if captcha.decode("utf-8").lower() != code.lower():
            logininfor = cls.build_logininfor(
                username, 
                Constants.LOGIN_FAIL, 
                MessageUtil.message("user.jcaptcha.error")
            )
            TaskManager.execute(record_logininfor,logininfor)
            raise ServiceException("验证码错误")
    
    @classmethod
    def record_sysuser(cls, id: int):
        """
        记录登录信息

        Args:
            id (int): 用户id
        """
        sysuser = SysUser(
            user_id=id,
            login_ip=IpUtil.get_ip(),
            login_date=datetime.datetime.now()
            )
        SysUserService.update_user_login_info(sysuser)
    
    @classmethod
    def build_logininfor(cls, username:str,status:str,message:str) -> SysLogininfor:
        """
        构建登录信息

        Args:
            username (str): 用户名
            status (str): 登录状态
            message (str): 登录信息

        Returns:
            SysLogininfor: 登录信息
        """
        ip = IpUtil.get_ip()
        address = AddressUtil.get_address(ip)
        browser = UserAgentUtil.browser()
        os = UserAgentUtil.os()
        
        logininfor = SysLogininfor(
            user_name=username,
            ipaddr=ip,
            login_location=address,
            browser=browser,
            os=os,
            msg=message,
            login_time=datetime.datetime.now()
        )
        if status in [Constants.LOGIN_SUCCESS, Constants.LOGOUT, Constants.REGISTER]:
            logininfor.status = Constants.SUCCESS
        else:
            logininfor.status = Constants.FAIL
        return logininfor

    @classmethod
    def logout(cls) -> bool:
        '''
        退出登录
        
        Returns:
            bool: 是否退出成功
        '''
        login_user:LoginUser = TokenService.get_login_user(request=request)
        if login_user:
            TokenService.del_login_user(token=login_user.token.hex)
            logininfor = cls.build_logininfor(
                login_user.user_name,
                Constants.LOGIN_SUCCESS, 
                "退出成功")
            TaskManager.execute(record_logininfor,logininfor)
        return True


@lm.unauthorized_handler
def unauthorized_handler() -> tuple[str, int]:
    """
    未授权处理

    Returns:
        tuple[str, int]: 返回401状态码
    """
    return "Unauthorized", 401


@lm.request_loader
def load_request(request:Request) -> LoginUser:
    """
    加载请求

    Args:
        request (Request): 请求

    Returns:
        LoginUser: 登录用户
    """
    login_user = TokenService.get_login_user(request)
    return login_user
