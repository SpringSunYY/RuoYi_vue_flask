# -*- coding: utf-8 -*-
"""
自定义缓存装饰器，复刻 Java 版 `@CustomCacheable` 的核心能力：
按照前缀、字段路径以及完整参数组合构造缓存 Key，并可选支持分页缓存。
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
import logging
from datetime import datetime
from typing import Any, Callable, List, Mapping, MutableMapping, Tuple

from werkzeug.local import LocalProxy

from ruoyi_admin.ext import redis_cache

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 30
DEFAULT_PAGE_NUM = 1
COMMON_SEPARATOR = ":"
ARGS_HASH_PREFIX = "args"


def _default_json_serializable(obj: Any) -> Any:
    """把任何返回值转成纯 JSON 可序列化（dict/list/原生类型）。"""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_default_json_serializable(v) for v in obj]
    if hasattr(obj, "model_dump"):
        return _default_json_serializable(obj.model_dump(mode="python"))
    if hasattr(obj, "__dict__"):
        result = {}
        for k, v in vars(obj).items():
            if not k.startswith("_"):
                result[k] = _default_json_serializable(v)
        return result
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def _serialize_for_cache(result: Any, func: Callable) -> bytes:
    """
    将返回值序列化为 JSON bytes。优先用 Pydantic model_dump，否则用通用递归转换。
    """
    try:
        # 有 model_dump 的对象（主要是 Pydantic）直接序列化，避免走到通用逻辑
        if hasattr(result, "model_dump"):
            data = result.model_dump(mode="python")
        elif isinstance(result, (list, tuple)):
            data = [
                item.model_dump(mode="python") if hasattr(item, "model_dump") else _default_json_serializable(item)
                for item in result
            ]
        else:
            data = _default_json_serializable(result)
        return json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    except Exception:
        # 兜底：通用递归序列化
        return json.dumps(_default_json_serializable(result), ensure_ascii=False, default=str).encode("utf-8")


def _deserialize_cached(cached: bytes, func: Callable) -> Any:
    """
    从 Redis bytes 反序列化为 Python 对象。
    利用函数返回类型注解自动重建 Pydantic 模型实例。
    """
    data = json.loads(cached.decode("utf-8"))
    rt = func.__annotations__.get("return")

    if rt is None:
        return data

    # 解析返回值类型
    origin = getattr(rt, "__origin__", None)
    if origin is list or origin is List:
        # List[SomeType] → list of model instances
        inner = getattr(rt, "__args__", (None,))[0]
        if inner is not None and hasattr(inner, "model_validate"):
            return [inner.model_validate(item) for item in data]
        return data
    elif origin is tuple or origin is Tuple:
        inner = getattr(rt, "__args__", ())
        return tuple(
            m.model_validate(item) if hasattr(m, "model_validate") else item
            for m, item in zip(inner, data)
        )
    elif hasattr(rt, "model_validate"):
        return rt.model_validate(data)
    return data


def custom_cacheable(
        key_prefix: str,
        key_field: str | None = None,
        use_query_params_as_key: bool = False,
        expire_time: int = 300,
        paginate: bool = False,
        page_number_field: str = "page_num",
        page_size_field: str = "page_size",
) -> Callable:
    """
    Redis 缓存装饰器，参数含义与用户给出的 Java 版注解保持一致，便于迁移。

    示例：
        @custom_cacheable(
            key_prefix="recruit:list",
            key_field="query.company_id",
            paginate=True,
            page_number_field="query.page_num",
            page_size_field="query.page_size",
        )
        def list_recruit(query: RecruitQuery):
            ...
    """

    def decorator(func: Callable) -> Callable:
        signature = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            client = _resolve_redis_client()
            if client is None or expire_time <= 0:
                return func(*args, **kwargs)

            bound_args = signature.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()
            params = bound_args.arguments  # OrderedDict：保留原始参数顺序

            base_key_segments = [key_prefix] if key_prefix else []

            if key_field:
                field_value = _get_value_by_field_path(params, key_field)
                if field_value not in (None, ""):
                    base_key_segments.append(str(field_value))

            if use_query_params_as_key:
                args_hash = _hash_arguments(params)
                base_key_segments.append(f"{ARGS_HASH_PREFIX}:{args_hash}")

            if not base_key_segments:
                # 如果开发者没有提供前缀，则退回到函数限定名，避免空 key。
                base_key_segments.append(func.__qualname__)

            cache_key = COMMON_SEPARATOR.join(base_key_segments)

            if paginate:
                page_number = _extract_int_value(params, page_number_field, DEFAULT_PAGE_NUM)
                page_size = _extract_int_value(params, page_size_field, DEFAULT_PAGE_SIZE)
                cache_key = (
                    f"{cache_key}{COMMON_SEPARATOR}{page_number}{COMMON_SEPARATOR}{page_size}"
                )
            else:
                page_number = page_size = None

            cached = _safe_redis_get(client, cache_key)
            if cached is not None:
                try:
                    return _deserialize_cached(cached, func)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("反序列化缓存数据失败 %s: %s", cache_key, exc)

            result = func(*args, **kwargs)

            # 开启分页时仅缓存列表或元组，避免单个对象导致缓存结构不一致。
            if paginate and not isinstance(result, (list, tuple)):
                return result

            try:
                payload = _serialize_for_cache(result, func)
            except Exception as exc:  # noqa: BLE001
                logger.warning("序列化缓存数据失败 %s: %s", cache_key, exc)
                return result

            _safe_redis_setex(client, cache_key, int(expire_time), payload)
            return result

        return wrapper

    return decorator


def _resolve_redis_client() -> LocalProxy | None:
    """
    兼容 Flask LocalProxy 的获取逻辑，若无上下文则直接放弃缓存。
    """

    try:
        return redis_cache
    except RuntimeError:
        logger.debug("当前无应用上下文，跳过缓存调用")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("获取 redis 连接失败: %s", exc)
        return None


def _safe_redis_get(client: LocalProxy, cache_key: str) -> bytes | None:
    """
    捕获 Redis 异常，防止缓存故障影响主流程。
    """

    try:
        return client.get(cache_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取缓存失败 %s: %s", cache_key, exc)
        return None


def _safe_redis_setex(client: LocalProxy, cache_key: str, expire: int, payload: bytes) -> None:
    """
    setex 包装，写入失败时仅记录日志。
    """

    try:
        client.setex(cache_key, expire, payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("写入缓存失败 %s: %s", cache_key, exc)


def _hash_arguments(params: Mapping[str, Any]) -> str:
    """
    将参数转为稳定 JSON，并计算 SHA1，避免直接存储长 JSON。
    """

    normalized = _normalize_for_hash(params)
    serialized = json.dumps(normalized, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def _normalize_for_hash(value: Any) -> Any:
    """
    递归展开常见类型，保证同样语义的参数能得到一致的哈希。
    """

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(k): _normalize_for_hash(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_for_hash(v) for v in value]
    if hasattr(value, "__dict__"):
        data = {
            k: _normalize_for_hash(v)
            for k, v in vars(value).items()
            if not k.startswith("_")
        }
        if data:
            return data
    return repr(value)


def _get_value_by_field_path(params: MutableMapping[str, Any], field_path: str) -> Any:
    """
    按“参数名.属性.子属性”路径提取嵌套值。
    """

    if not field_path:
        return None
    parts = field_path.split(".")
    if not parts:
        return None

    target = params.get(parts[0])
    for part in parts[1:]:
        if target is None:
            return None
        target = _dig_value(target, part)
    return target


def _dig_value(value: Any, attribute: str) -> Any:
    """
    支持字典、列表（下标）、对象属性的通用取值方法。
    """

    if value is None:
        return None
    if isinstance(value, Mapping):
        return value.get(attribute)
    if isinstance(value, (list, tuple)):
        if attribute.isdigit():
            index = int(attribute)
            if 0 <= index < len(value):
                return value[index]
        return None
    return getattr(value, attribute, None)


def _extract_int_value(
        params: MutableMapping[str, Any], field_path: str | None, default_value: int
) -> int:
    """
    读取分页参数，自动完成类型转换及异常兜底。
    """

    if not field_path:
        return default_value
    raw_value = _get_value_by_field_path(params, field_path)
    if raw_value is None or isinstance(raw_value, bool):
        return default_value
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default_value
