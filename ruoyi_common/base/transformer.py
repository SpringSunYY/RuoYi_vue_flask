from types import NoneType
from typing import Callable, List, Optional
from datetime import datetime
from typing_extensions import Annotated
from pydantic import BeforeValidator, ValidationInfo

from ruoyi_common.utils.base import DateUtil


def ids_to_list(value: str) -> Optional[List[int]]:
    """
    验证ids转换为字符串列表

    Args:
        value (str | NoneType): 传入参数

    Returns:
        Optional[List[str]]: 列表
    """
    return [int(i) for i in value.split(',')]


def to_datetime(format=None) -> Callable[[str | NoneType, ValidationInfo], datetime | NoneType]:
    """
    根据指定格式，验证datetime

    Args:
        format (str): 日期格式. Defaults to '%Y-%m-%d %H:%M:%S'.
    """
    if format is None:
        # 默认支持常见的年月日格式，以及仅到月份的格式，方便 Excel 导入
        formats: List[str] = [
            DateUtil.YYYY_MM_DD_HH_MM_SS,
            DateUtil.YYYY_MM_DD,
            "%Y.%m",
            "%Y-%m",
        ]
    elif isinstance(format, (list, tuple, set)):
        formats = list(format)
    else:
        formats = [format]

    def validate_datetime(value: str | NoneType, info: ValidationInfo) -> datetime | NoneType:
        """
        验证datetime

        Args:
            value (str | NoneType): 传入参数
            info (ValidationInfo): pydantic的验证信息

        Raises:
            ValueError: 日期格式错误

        Returns:
            _type_: datetime
        """
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            raise ValueError(f"time data '{value}' does not match formats: {formats}")
        raise ValueError(f"Invalid datetime format: {value}")

    return validate_datetime


def str_to_int(value: str | NoneType, info: ValidationInfo) \
        -> int:
    """
    验证str是否为整数，并转换为整数

    Args:
        value (str | NoneType): 传入参数
        info (ValidationInfo): pydantic的验证信息

    Raises:
        ValueError: 字符串格式错误

    Returns:
        int: 整数
    """
    if value:
        if isinstance(value, str):
            if value.isdecimal():
                return int(value)
            else:
                raise ValueError(f"Invalid str format, cannot convert to int: {value}")
    return value


def str_to_float(value: str | NoneType, info: ValidationInfo) -> float | NoneType:
    """
    将字符串转换为浮点数；空值直接返回
    """
    if value is None or value == "":
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        try:
            return float(stripped)
        except ValueError:
            # 格式化不了就返回 None，避免抛出验证错误
            return None
    return value


def int_to_str(value: int | NoneType) -> str:
    if isinstance(value, int):
        return str(value)
    else:
        return value


ids_convertor = Annotated[List[int], BeforeValidator(ids_to_list)]
