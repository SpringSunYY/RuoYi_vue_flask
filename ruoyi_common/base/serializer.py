# -*- coding: utf-8 -*-
# @Author  : YY

import dataclasses
from datetime import date
import decimal
import uuid
import typing as t
from flask import Response
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException, default_exceptions
from werkzeug.http import http_date

from ruoyi_common.base.model import AjaxResponse
from ruoyi_common.constant import HttpStatus
from ruoyi_common.utils.base import UtilException

WSGIEnvironment: t.TypeAlias = dict[str, t.Any]


def _update_exceptions():
    """
    更新异常
    """
    for code in default_exceptions.keys():
        exc = default_exceptions[code]
        if isinstance(exc, HTTPException):
            new_exc = HttpException.from_http_exception(exc)
            default_exceptions[code] = new_exc
        else:
            continue


_update_exceptions()
del _update_exceptions


class HttpException(HTTPException):

    code: int | None = None
    description: str | None = None

    def __init__(
        self,
        description: str | None = None,
        response: Response | None = None,
    ) -> None:
        super().__init__()
        if description is not None:
            self.description = description
        self.response = response

    @classmethod
    def from_http_exception(cls, exc: HTTPException) -> "HttpException": 
        """
        从HTTPException转换为HttpException

        Args:
            exc (HTTPException): werkezeug的HTTPException

        Returns:
            HttpException: HttpException
        """
        error = cls(description=exc.description, response=exc.response)
        error.code = exc.code
        return error
    
    @property
    def name(self) -> str:
        """
        状态名称
        
        Returns:
            str: 状态名称
        """
        from werkzeug.http import HTTP_STATUS_CODES

        return HTTP_STATUS_CODES.get(self.code, "Unknown Error")  # type: ignore

    def get_description(
        self,
        environ: WSGIEnvironment | None = None,
        scope: dict[str, t.Any] | None = None,
    ) -> str:
        """
        异常描述
        
        Args:
            environ (WSGIEnvironment, optional): 环境变量. Defaults to None.
            scope (dict[str, t.Any], optional): 作用域. Defaults to None.

        Returns:
            str: 异常描述
        """
        return self.description or ""

    def get_body(
        self,
        environ: WSGIEnvironment | None = None,
        scope: dict[str, t.Any] | None = None,
    ) -> str:
        """
        异常响应体
        
        Args:
            environ (WSGIEnvironment, optional): 环境变量. Defaults to None.
            scope (dict[str, t.Any], optional): 作用域. Defaults to None.

        Returns:
            str: 异常响应体
        """
        ajax_resposne = AjaxResponse.from_error(msg=self.description)
        ajax_resposne.code = self.code
        return ajax_resposne.model_dump_json(
            exclude_unset = True,
            exclude_none = True,
        )

    def get_headers(
        self,
        environ: WSGIEnvironment | None = None,
        scope: dict[str, t.Any] | None = None,
    ) -> list[tuple[str, str]]:
        """
        异常请求头
        
        Args:
            environ (WSGIEnvironment, optional): 环境变量. Defaults to None.
            scope (dict[str, t.Any], optional): 作用域. Defaults to None.

        Returns:
            list[tuple[str, str]]: 异常请求头
        """
        return [("Content-Type", "application/json")]


def json_default(obj):
    """
    转化成可序列化对象

    Args:
        obj : 待序列化对象

    Returns:
        _type_: 可序列化对象
    """
    if isinstance(obj, date):
        return http_date(obj) 

    if isinstance(obj, decimal.Decimal):
        return str(obj)
    
    if isinstance(obj, uuid.UUID):
        return obj.hex

    if dataclasses and dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)

    if isinstance(obj, AjaxResponse):
        return obj.model_dump_json()

    if hasattr(obj, "__html__"):
        return str(obj.__html__())

    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class JsonProvider(DefaultJSONProvider):
    """
    自定义json序列化

    Args:
        DefaultJSONProvider: 默认flask的json序列化
    """
    
    default = staticmethod(json_default)


def handle_http_exception(error:HTTPException) -> Response:
    """
    处理http异常

    Args:
        error (HttpException): http异常

    Returns:
        ResponseReturnValue: 响应体
    """
    if not isinstance(error, HttpException):
        error = HttpException.from_http_exception(error)
    return error.get_response()


def handle_util_exception(error:UtilException) -> Response:
    """
    处理业务工具类异常，保持和若依Java版一致的json结构
    """
    status = getattr(error, "status", HttpStatus.ERROR)
    ajax_response = AjaxResponse.from_error(msg=str(error))
    ajax_response.code = status
    response = Response(
        response=ajax_response.model_dump_json(
            exclude_unset=True,
            exclude_none=True,
        ),
        status=status,
        mimetype="application/json"
    )
    return response
