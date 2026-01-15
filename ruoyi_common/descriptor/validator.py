
import inspect
from abc import ABC, abstractmethod
from functools import wraps
from dataclasses import dataclass, field
from typing import Annotated, Any, Callable, Dict, Tuple, Type, ClassVar, \
    Optional, Set
from werkzeug.exceptions import BadRequest, InternalServerError
from flask import has_request_context, request
from pydantic import BaseModel, ValidationError, validate_call
from pydantic.fields import FieldInfo

from ruoyi_common.base.model import MultiFile
from ruoyi_common.base.reqparser import BaseReqParser, BodyReqParser, \
    DownloadFileQueryReqParser, UploadFileFormReqParser, PathReqParser, \
    QueryReqParser, VoValidatorContext
from ruoyi_common.base.schema_vo import ArbitrarySchemaFactory, \
    BaseSchemaFactory, BodySchemaFactory, PathSchemaFactory, QuerySchemaFactory


class AbcValidatorFunction(ABC):

    @abstractmethod
    def validate_unbound_parameters(self):
        raise NotImplementedError()

    @abstractmethod
    def validate_function(self):
        raise NotImplementedError()

    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError()


class ValidatorScopeFunction(AbcValidatorFunction):

    def __init__(self,func:Callable):
        self.func = func
        self.sig = inspect.signature(self.func)
        self._unbound_fields:Dict[str,Annotated] = {}
        self._unbound_model: \
            Optional[Tuple[str,Type[BaseModel],Type[BaseModel]]] = None
        self.args = ()
        self.kwargs = {}
        self.validate_unbound_parameters()
        self.validate_function()

    @property
    def unbound_model(self):
        return self._unbound_model

    def _validate_kind(self,kind):
        if kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise Exception("参数必须是位置参数")

    def validate_unbound_parameters(self):
        index = 0
        for key in self.sig.parameters:
            param = self.sig.parameters[key]
            self._validate_kind(param.kind)
            if inspect.isclass(param.annotation) and issubclass(param.annotation, BaseModel):
                # 检查是否是BaseEntity的子类（业务对象）
                from ruoyi_common.base.model import BaseEntity
                if issubclass(param.annotation, BaseEntity):
                    self._unbound_model = (key,param.annotation)
                    # 不限制只能是第一个参数，允许类方法中的业务对象参数
                    break  # 找到第一个BaseEntity子类就停止
                else:
                    print(f"参数 {key} 不是 BaseEntity 子类")
            else:
                self._unbound_fields[key] = \
                    FieldInfo.from_annotation(param.annotation)
            index += 1

    def validate_function(self):
        self.func = validate_call(self.func)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.args = args if args else ()
        self.kwargs = kwargs if kwargs else {}
        return self.func(*self.args, **self.kwargs)


class ValidatorViewFunction(AbcValidatorFunction):

    def __init__(self,func:Callable):
        self.func = func
        self.sig = inspect.signature(self.func)
        self._unbound_fields:Dict[str,Annotated] = {}
        self._unbound_model: \
            Optional[Tuple[str,Type[BaseModel],Type[BaseModel]]] = None
        self._schema_factory = None
        self._data_parser = None
        self.args = ()
        self.kwargs = {}

    @property
    def unbound_model(self):
        return self._unbound_model

    def _validate_kind(self,kind):
        if kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise Exception("参数必须是位置参数")

    def validate_unbound_parameters(self):
        index = 0
        for key in self.sig.parameters:
            param = self.sig.parameters[key]
            self._validate_kind(param.kind)
            if self._schema_factory:
                annotation = self._schema_factory. \
                    validate_annotation(param.annotation)
                if annotation:
                    self._unbound_model = (key,annotation)
                    if index > 0:
                        raise Exception(
                            f"{self.func.__name__} 类型参数有且仅有第一个"
                        )
                else:
                    self._unbound_fields[key] = \
                        FieldInfo.from_annotation(param.annotation)
            else:
                if isinstance(param.annotation, BaseModel):
                    self._unbound_model = (key,param.annotation)
                    if index > 0:
                        raise Exception(
                            f"{self.func.__name__} 类型参数有且仅有第一个"
                        )
                else:
                    self._unbound_fields[key] = \
                        FieldInfo.from_annotation(param.annotation)
            index += 1

    def validate_function(self):
        if self._schema_factory:
            if self._unbound_model:
                self.func = validate_call(
                    self.func,
                    config=self._schema_factory.model_config)
            else:
                self.func = validate_call(
                    self.func,
                    config=self._schema_factory.model_config
                )
        else:
            self.func = validate_call(self.func)

    def unbound_data(
            self,
            data_parser: BaseReqParser
    ):
        self._data_parser = data_parser
        if self._schema_factory and self._data_parser:
            self._data_parser.prepare_factory(self._schema_factory)

    def unbound_schema(
            self,
            schema_factory:Optional[BaseSchemaFactory],
    ):
        self._schema_factory = schema_factory
        self.validate_unbound_parameters()
        self.validate_function()

    def bound_data(self, args:Tuple=(), kwargs:Dict={}):
        if self._unbound_model:
            key, bo_model = self._unbound_model
            obj = self._data_parser.cast_model(bo_model)
            kwargs[key] = obj
        else:
            # 特殊处理文件上传参数（MultiFile），直接从 request.files 构造
            has_multi_file_param = any(
                param.annotation is MultiFile
                for param in self.sig.parameters.values()
            )
            if has_multi_file_param:
                files = MultiFile.from_obj(request.files)
                kwargs.clear()
                for name, param in self.sig.parameters.items():
                    if param.annotation is MultiFile:
                        kwargs[name] = files
                return

            data = self._data_parser.data()
            kwargs.clear()
            kwargs.update(data)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.args = args if args else ()
        self.kwargs = kwargs if kwargs else {}
        if not has_request_context:
            raise Exception("请在flask请求上下文中调用")
        try:
            if self._data_parser:
                self._data_parser.prepare()
                self.bound_data(self.args, self.kwargs)
        except ValidationError as e:
            return BadRequest(description=str(e))
        except TypeError as e:
            return BadRequest(description=str(e))
        except Exception as e:
            return InternalServerError(description=str(e))
        else:
            return self.func(*self.args, **self.kwargs)


@dataclass
class BaseValidator:

    data_parser:ClassVar = None

    schema_factory:ClassVar = None

    vo_context:VoValidatorContext = field(init=False)

    def __call__(self, func):

        view_function = ValidatorViewFunction(func)
        view_function.unbound_schema(self.schema_factory)
        view_function.unbound_data(self.data_parser)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return view_function(*args, **kwargs)
        return wrapper


@dataclass
class PathValidator(BaseValidator):

    def __post_init__(self):
        self.schema_factory = PathSchemaFactory()
        self.data_parser = PathReqParser()


@dataclass
class QueryValidator(BaseValidator):

    is_page: bool = False

    include:Optional[Set[str]] = field(default=None)

    exclude:Optional[Set[str]] = field(default=None)

    extra_fields:Optional[Dict[str, FieldInfo]] = field(default=None)

    def __post_init__(self):
        vo_context = VoValidatorContext(
            exclude_data_alias=True,
            is_page=self.is_page,
            is_sort=self.is_page,
            include_fields=self.include,
            exclude_fields=self.exclude,
        )
        self.schema_factory = QuerySchemaFactory(
            vo_context,
            extra_strict_forbid=True,
            extra_allowed_fields=self.extra_fields
        )
        self.data_parser = QueryReqParser(vo_context)


@dataclass
class BodyValidator(BaseValidator):

    include:Optional[Set[str]] = field(default=None)
    exclude:Optional[Set[str]] = field(default=None)

    def __post_init__(self):
        vo_context = VoValidatorContext(
            include_fields=self.include,
            exclude_fields=self.exclude
        )
        self.schema_factory = BodySchemaFactory(vo_context)
        self.data_parser = BodyReqParser(vo_context)


@dataclass
class FileDownloadValidator(BaseValidator):

    def __post_init__(self):
        vo_context = VoValidatorContext(
            exclude_data_alias=True,
            is_page=True,
        )
        self.schema_factory = QuerySchemaFactory(vo_context)
        self.data_parser = DownloadFileQueryReqParser(vo_context)


@dataclass
class FileUploadValidator(BaseValidator):

    def __post_init__(self):
        self.schema_factory = ArbitrarySchemaFactory()
        self.data_parser = UploadFileFormReqParser(
            is_form=False, is_query=True, is_file=True
        )


@dataclass
class FileValidator(BaseValidator):

    include:Optional[Set[str]] = field(default=None)

    def __post_init__(self):
        self.schema_factory = ArbitrarySchemaFactory()
        self.data_parser = UploadFileFormReqParser()
