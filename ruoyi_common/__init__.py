# -*- coding: utf-8 -*-
# @Author  : YY

import os
import sys
from types import ModuleType
from werkzeug.exceptions import HTTPException

from ruoyi_common.base.serializer import JsonProvider,handle_http_exception,handle_util_exception
from ruoyi_common.descriptor.listener import ModuleSignalListener
from ruoyi_common.base.signal import module_initailize
from ruoyi_common.ruoyi.registry import RuoYiModuleRegistry
from ruoyi_common.utils.base import UtilException


@ModuleSignalListener(sys.modules[__name__],module_initailize)
def import_hook(module:ModuleType, registry:RuoYiModuleRegistry):
    """
    导入模块
    初始化app的一些操作：
        1.注册json序列化器
        2.注册错误处理器

    Args:
        module: 模块对象
        module_register: 模块注册器
    """
    os.environ['WERKZEUG_DEBUG_PIN'] = 'off'
        
    registry.app.json_provider_class = JsonProvider
    
    registry.app.register_error_handler(
        HTTPException, handle_http_exception
    )
    registry.app.register_error_handler(
        UtilException, handle_util_exception
    )
