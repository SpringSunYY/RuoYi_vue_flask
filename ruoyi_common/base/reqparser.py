from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Dict, Iterable, Set, Type

from flask import g, request
from pydantic import AliasChoices, AliasPath, BaseModel
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from ruoyi_common.base.model import CriterianMeta, ExtraModel, \
    BaseEntity, OrderModel, PageModel, VoValidatorContext
from ruoyi_common.base.schema_vo import BaseSchemaFactory, QuerySchemaFactory


class AbsReqParser(ABC):

    @abstractmethod
    def data(self) -> Dict:
        """
        获取请求参数

        Returns:
            Dict: 请求参数字典
        """

    @abstractmethod
    def cast_model(self, bo_model: BaseEntity) -> BaseModel:
        """
        适配模型

        Args:
            bo_model (BaseEntity): Vo模型
            src_model (BaseModel): 源模型

        Returns:
            BaseModel: 适配后的模型
        """

    @abstractmethod
    def prepare_factory(self, factory: BaseSchemaFactory):
        """
        准备工厂

        Args:
            factory (BaseSchemaFactory): 工厂
        """

    @abstractmethod
    def prepare(self):
        """
        准备数据
        """


class BaseReqParser(AbsReqParser):

    def data(self) -> Dict:
        pass

    def cast_model(self, bo_model: BaseEntity) -> BaseModel:
        pass

    def prepare_factory(self, factory: BaseSchemaFactory):
        pass

    def prepare(self):
        pass


class QueryReqParser(BaseReqParser):

    def __init__(self, context: VoValidatorContext):
        self.context = context
        self.extra_model = ExtraModel

    def prepare_factory(self, factory: QuerySchemaFactory):
        if factory.extra_model:
            self.extra_model = factory.extra_model

    def prepare(self):
        self.criterian_meta = CriterianMeta()
        g.criterian_meta = self.criterian_meta

    def validate_request(self) -> Dict:
        data = request.args.to_dict()
        # 兼容前端传参形式 params[xxx]=yyy
        params_dict = {}
        for key, val in list(data.items()):
            if key.startswith("params[") and key.endswith("]"):
                inner = key[len("params["):-1]
                params_dict[inner] = val
                data.pop(key, None)
        if params_dict:
            data["params"] = params_dict
        return data

    def data(self) -> Dict:
        data = self.validate_request().copy()
        if self.context.is_page:
            page = PageModel.model_validate(data, context=self.context)
            if page.model_fields_set:
                self.criterian_meta.page = page
            self._remove_model_aliases(data, PageModel)
        if self.context.is_sort:
            sort = OrderModel.model_validate(data, context=self.context)
            if sort.model_fields_set:
                self.criterian_meta.sort = sort
            self._remove_model_aliases(data, OrderModel)
        if self.extra_model:
            # 使用数据副本验证 ExtraModel，避免修改原始数据
            extra_data_copy = data.copy()
            extra = self.extra_model.model_validate(extra_data_copy, context=self.context)
            if extra.model_fields_set:
                self.criterian_meta.extra = extra
                # 移除别名，但保留可能被主模型使用的通用别名
                reserved_aliases = {'startTime', 'endTime', 'beginTime', 'pageNum', 'pageSize', 'orderByColumn', 'isAsc'}
                for alias in self._collect_aliases(self.extra_model):
                    if alias not in reserved_aliases:
                        data.pop(alias, None)
        return data

    def cast_model(self, bo_model: BaseEntity) -> BaseModel:
        data = self.data()
        # 对于查询参数，只保留模型中定义的字段和别名，忽略额外字段
        # 收集模型中所有字段名和别名
        model_fields = set()
        for name, info in bo_model.model_fields.items():
            model_fields.add(name)
            # 添加查询别名（camelCase）
            if hasattr(bo_model, 'model_config') and bo_model.model_config:
                alias_gen = bo_model.model_config.get('alias_generator')
                if callable(alias_gen):
                    alias = alias_gen(name)
                    model_fields.add(alias)
            # 添加 validation_alias
            if info.validation_alias:
                if isinstance(info.validation_alias, str):
                    model_fields.add(info.validation_alias)
                elif hasattr(info.validation_alias, 'choices'):
                    model_fields.update(info.validation_alias.choices)
        # 过滤掉未定义的字段，保持别名格式供模型验证
        filtered_data = {k: v for k, v in data.items() if k in model_fields}
        bo = bo_model.model_validate(filtered_data)
        return bo

    def _remove_model_aliases(
            self,
            data: Dict[str, str],
            model_cls: Type[BaseModel]
    ) -> None:
        """
        删除已经用于解析的模型字段别名，避免后续模型校验时报额外字段错误
        """
        if not data:
            return
        for alias in self._collect_aliases(model_cls):
            data.pop(alias, None)

    def _collect_aliases(self, model_cls: Type[BaseModel]) -> Set[str]:
        alias_set: Set[str] = set()
        populate_by_name = getattr(model_cls, "model_config", {}).get(
            "populate_by_name", False
        )
        for name, info in model_cls.model_fields.items():
            alias_set.update(self._field_aliases(name, info, populate_by_name))
        return alias_set

    @staticmethod
    def _field_aliases(
            name: str,
            info,
            populate_by_name: bool
    ) -> Iterable[str]:
        aliases: Set[str] = set()
        if getattr(info, "alias", None):
            aliases.add(info.alias)
        validation_alias = getattr(info, "validation_alias", None)
        if isinstance(validation_alias, str):
            aliases.add(validation_alias)
        elif isinstance(validation_alias, AliasChoices):
            aliases.update(validation_alias.choices)
        elif isinstance(validation_alias, AliasPath):
            pass
        if populate_by_name:
            aliases.add(name)
        return aliases


@dataclass
class PathReqParser(BaseReqParser):

    def data(self) -> Dict:
        return request.view_args.copy()


@dataclass
class BodyReqParser(BaseReqParser):
    minetype: ClassVar[str] = "application/json"

    def __init__(self, context: VoValidatorContext):
        self.context = context

    def validate_request(self) -> Dict:
        content_type = request.headers.get("Content-Type", "").lower()
        minetype = content_type.split(";")[0]
        if minetype == self.minetype:
            body: dict | list = request.get_json()
            if not body:
                raise BadRequest(
                    description="在{}, body数据不能为空".format(content_type),
                )
        else:
            raise UnsupportedMediaType(
                description="content-type仅支持application/json"
            )
        return body

    def data(self) -> Dict:
        data = self.validate_request().copy()
        return data

    def cast_model(self, bo_model: BaseEntity) -> BaseModel:
        data = self.data()
        bo = bo_model.model_validate(data, context=self.context)
        return bo


@dataclass
class FormUrlencodedQueryReqParser(QueryReqParser):
    minetype: ClassVar[str] = "application/x-www-form-urlencoded"

    def __init__(self, context: VoValidatorContext):
        super().__init__(context)

    def validate_request(self) -> Dict:
        content_type = request.headers.get("Content-Type", "").lower()
        minetype = content_type.split(";")[0]
        if minetype == self.minetype:
            form: ImmutableMultiDict = request.form
            body = form.to_dict()
        else:
            raise UnsupportedMediaType(
                description="除了{},content-type不支持{}".format(self.minetype, minetype)
            )
        return body


@dataclass
class DownloadFileQueryReqParser(FormUrlencodedQueryReqParser):

    def __init__(self, context: VoValidatorContext):
        super().__init__(context)


class FormReqParser(BaseReqParser):
    minetype: ClassVar[str] = "multipart/form-data"

    def __init__(
            self,
            is_form: bool = True,
            is_query: bool = False,
            is_file: bool | None = None,
    ):
        self.is_form = is_form
        self.is_query = is_query
        self.is_file = is_file

    def validate_request(self) -> Dict:
        content_type = request.headers.get("Content-Type", "").lower()
        minetype = content_type.split(";")[0]
        new_data = {}
        if minetype == self.minetype:
            if self.is_form:
                new_data.update(request.form.to_dict())
            if self.is_query:
                new_data.update(request.args.to_dict())
            if self.is_file:
                new_data.update(request.files.to_dict(flat=False))
        else:
            raise UnsupportedMediaType(
                description="除了{},content-type不支持{}".format(self.minetype, minetype)
            )
        return new_data

    def data(self) -> Dict:
        data = self.validate_request()
        return data


class UploadFileFormReqParser(FormReqParser):

    def validate_request(self) -> Dict:
        return super().validate_request()

    def data(self) -> Dict:
        data = self.validate_request()
        return data


class StreamReqParser(BaseReqParser):
    minetype: ClassVar[str] = "application/octet-stream"

    def data(self, *args, **kwargs) -> Dict:
        pass
