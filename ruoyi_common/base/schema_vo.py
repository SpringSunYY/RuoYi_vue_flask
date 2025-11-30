# -*- coding: utf-8 -*-
# @Author  : YY

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Type, Dict, Optional, Set, Tuple, TypeVar
from pydantic.alias_generators import to_camel
from pydantic import AliasChoices, AliasGenerator, AliasPath, BaseModel, ConfigDict, Field, create_model
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from pydantic import BaseModel

from ruoyi_common.base.model import AllowedExtraModel, BaseEntity, BetOpt, ExtraModel, ExtraOpt, MultiFile, VoAccess, \
    VoValidatorContext
from ruoyi_common.utils.base import DateUtil, get_final_model

T = TypeVar("T")

strict_valid_config = ConfigDict(
    from_attributes=False,
    alias_generator=to_camel,
    frozen=True,
    extra="forbid",
    strict=True,
    populate_by_name=False,
    json_encoders={
        datetime: lambda v: v.strftime(DateUtil.YYYY_MM_DD_HH_MM_SS)
    },
)

query_valid_config = ConfigDict(
    from_attributes=False,
    alias_generator=to_camel,
    frozen=True,
    extra="allow",
    strict=True,
    populate_by_name=False,
)


def VoField(
        body=True,
        query=False,
        sort=False,
        *args,
        **kwargs
):
    vo = VoAccess(
        body=body,
        query=query,
        sort=sort,
    )
    return Field(vo=vo, *args, **kwargs)


class AbcFieldFilter(ABC):

    def filter(self, name: str, info: FieldInfo) -> bool:
        """
        过滤字段

        Args:
            name(str): 字段名称
            info(FieldInfo): 字段元信息

        Returns:
            bool: 是否过滤
        """


class BaseFieldFilter(AbcFieldFilter):

    def filter(self, name: str, info: FieldInfo) -> bool:
        """
        过滤字段

        Args:
            name(str): 字段名称
            info(FieldInfo): 字段元信息

        Returns:
            bool: 是否过滤
        """
        return False


class VoBodyFieldFilter(BaseFieldFilter):

    def __init__(self):
        self.action = "body"

    def filter(self, name: str, info: FieldInfo) -> bool:
        """
        过滤字段

        Args:
            name(str): 字段名称
            info(FieldInfo): 字段元信息

        Returns:
            bool: 是否过滤
        """
        default = True
        if info.json_schema_extra:
            vo_access: VoAccess = info.json_schema_extra.get("vo", default)
            if vo_access:
                perm = getattr(vo_access, self.action, default)
                if perm:
                    is_required = getattr(vo_access, "body_required", False)
                    if is_required:
                        self.change_to_required(info)
                    else:
                        self.change_to_optional(info)
                flag = perm
            else:
                flag = default
        else:
            flag = default
        return flag

    @classmethod
    def change_to_required(cls, info: FieldInfo):
        """
        将注解转换为必选项

        Args:
            info(FieldInfo): 字段元信息
        """
        info.default = PydanticUndefined
        info.default_factory = None

    @classmethod
    def change_to_optional(cls, info: FieldInfo):
        """
        将注解转换为可选项

        Args:
            info(FieldInfo): 字段元信息
        """
        if info.is_required:
            info.default = None


class VoQueryFieldFilter(BaseFieldFilter):
    extra_opt_cls_list = [BetOpt]

    def __init__(self):
        self.action = "query"
        self.sort_fields: Dict[str, FieldInfo] = {}
        self.extra_fields: Dict[str, ExtraOpt] = {}

    def filter(self, name: str, info: FieldInfo) -> bool:
        """
        根据权限信息，重置字段

        Args:
            name(str): 字段名称
            info(FieldInfo): 字段元信息

        Returns:
            Tuple[bool,bool]: 是否支持查询，是否支持排序
        """
        default = False
        if info.json_schema_extra:
            vo_access: VoAccess = info.json_schema_extra.get("vo", False)
            query_perm = getattr(vo_access, self.action, default)
            for extra_opt_cls in self.extra_opt_cls_list:
                if isinstance(query_perm, extra_opt_cls):
                    query_perm.name = name
                    query_perm.info = info
                    self.extra_fields[name] = query_perm
                    query_perm = False
                else:
                    continue
            sort_perm = getattr(vo_access, "sort", default)
            if sort_perm:
                self.sort_fields[name] = info
            return query_perm
        else:
            return default


class AbcSchemaFactory(ABC):

    @abstractmethod
    def validate_annotation(annotation: Type) -> Optional[Type]:
        """
        检查注解是否有效

        Args:
            annotation(Type): 注解

        Returns:
            Optional[Type]: 合法的类型
        """
        pass


class BaseSchemaFactory(AbcSchemaFactory):
    action = "base"
    model_config = query_valid_config

    def __init__(self):
        self.field_filter = None
        self.model_suffix = "Vo"

    def validate_annotation(self, annotation: Type) -> Optional[Type]:
        """
        检查注解是否有效

        Args:
            annotation(Type): 注解

        Returns:
            Optional[Type]: 合法的类型
        """
        bo_model = get_final_model(annotation)
        if issubclass(bo_model, BaseEntity):
            model = self.rebuild_model(model_cls=bo_model)
            return model
        else:
            return None

    def rebuild_model(self, model_cls: Type[BaseEntity]) -> Type[BaseEntity]:
        """
        从已有模型类，创建新的模型类

        Args:
            model_cls: 已有模型类

        Returns:
            Type[BaseModel]: 新的模型类
        """

        field_definitions = {}
        for name, info in model_cls.model_fields.items():
            flag = self.rebuild_field(name, info)
            if flag:
                field_definitions[name] = info.annotation, info
        vo_name = model_cls.__name__ + self.action.capitalize() + \
                  self.model_suffix

        # 如果是 QuerySchemaFactory，使用 query_valid_config 允许额外字段
        if hasattr(self, 'action') and self.action == 'query' and hasattr(self, 'model_config'):
            # 创建一个新的基类，使用 query_valid_config
            class QueryBaseModel(model_cls):
                model_config = self.model_config.copy()

            base_class = QueryBaseModel
        else:
            base_class = model_cls

        new_model = create_model(
            vo_name,
            __base__=base_class,
            __doc__=model_cls.__doc__,
            __module__=model_cls.__module__,
            **field_definitions
        )

        return new_model

    def rebuild_field(self, name: str, info: FieldInfo) -> bool:
        """
        重置字段

        Args:
            name(str): 字段名称
            info(FieldInfo): 字段元信息

        Returns:
            bool: 是否支持重置
        """
        return True


class BodySchemaFactory(BaseSchemaFactory):
    action = "body"
    model_config = query_valid_config

    def __init__(self, context: VoValidatorContext):
        super().__init__()
        self.context = context
        self.field_filter = VoBodyFieldFilter()

    def validate_annotation(self, annotation: Type) -> Optional[Type[BaseModel]]:
        bo_model = get_final_model(annotation)
        if issubclass(bo_model, BaseModel):
            updated_model = self.rebuild_model(model_cls=bo_model)
            return updated_model
        else:
            if self.context.include_fields or self.context.exclude_fields:
                raise Exception(f"注解{annotation.__name__}不是模型，不支持include和exclude请求条件")
            return None

    def rebuild_field(self, name: str, info: FieldInfo) -> bool:
        """
        重置字段

        Args:
            name(str): 字段名称
            info(FieldInfo): 字段元信息

        Returns:
            bool: 是否支持重置
        """
        if self.context.include_fields and \
                name not in self.context.include_fields:
            return False
        if self.context.exclude_fields and \
                name in self.context.exclude_fields:
            return False
        flag = self.field_filter.filter(name, info)
        return flag


class QuerySchemaFactory(BaseSchemaFactory):
    action = "query"
    model_config = query_valid_config

    def __init__(
            self,
            context,
            extra_strict_forbid=True,
            extra_allowed_fields: Type[Dict[str, FieldInfo]] = None
    ):
        super().__init__()
        self.context = context
        self.field_filter = VoQueryFieldFilter()
        self.extra_strict_forbid = extra_strict_forbid
        self.extra_allowed_fields = extra_allowed_fields
        self.extra_model = None

    def validate_annotation(self, annotation: Type) -> Optional[Type[BaseEntity]]:
        bo_model = get_final_model(annotation)
        if issubclass(bo_model, BaseEntity):
            updated_model = self.rebuild_model(model_cls=bo_model)
            # 使用 query_valid_config 而不是原模型的配置，允许额外字段
            self.model_config = self.model_config.copy()
            self._validate_context()
            self.rebuild_extra_model()
            return updated_model
        else:
            if self.context.include_fields or self.context.exclude_fields:
                raise Exception(f"注解{annotation.__name__}不是模型，不支持include和exclude请求条件")
            return None

    def _validate_context(self):
        """
        验证上下文信息
        """
        for name, info in self.field_filter.sort_fields.items():
            alias_set = self.get_validate_alias(name, info)
            self.context.include_sort_alias = self.context.include_sort_alias | alias_set

    def get_validate_alias(self, name: str, info: FieldInfo) -> Set[str]:
        """
        获取验证别名

        Args:
            name (str): 字段名称
            info (FieldInfo): 字段元信息

        Raises:
            Exception: 模型不支持AliasPath

        Returns:
            Set[str]: 别名集合
        """
        alias_set = set()
        alias = self.get_alias_from_config(name)
        if alias:
            alias_set.add(alias)
        if info.validation_alias:
            if isinstance(info.validation_alias, str):
                alias_set.add(info.validation_alias)
            elif isinstance(info.validation_alias, AliasPath):
                raise Exception(f"模型字段{name}不支持AliasPath")
            elif isinstance(info.validation_alias, AliasChoices):
                alias_set = alias_set | \
                            set(info.validation_alias.choices)
        if "populate_by_name" in self.model_config \
                and self.model_config["populate_by_name"]:
            alias_set.add(name)
        return alias_set

    def get_alias_from_config(self, name: str) -> Optional[str]:
        """
        从配置中获取别名

        Args:
            name (str): 字段名称

        Returns:
            Optional[str]: 别名
        """
        if "generate_alias" in self.model_config:
            generate_alias = self.model_config["generate_alias"]
            if callable(generate_alias):
                alias = generate_alias(name)
                return alias
            elif isinstance(generate_alias, AliasGenerator):
                alias, v_alias, s_alias = generate_alias(name)
                return alias or v_alias

    def rebuild_extra_model(self) -> Optional[Type[ExtraModel]]:
        """
        重新构建Extra查询模型

        Args:
            fields (Dict[str,ExtraOpt]): 字段元信息

        Returns:
            Optional[Type[ExtraModel]]: extra查询模型
        """
        field_defintions = {}
        for name, opt in self.field_filter.extra_fields.items():
            if isinstance(opt, BetOpt):
                min_fieldinfo, max_fieldinfo = self.rebuild_bet_opt(name, opt)
                field_defintions[opt.min] = min_fieldinfo.annotation, min_fieldinfo
                field_defintions[opt.max] = max_fieldinfo.annotation, max_fieldinfo
            elif isinstance(opt, ExtraOpt):
                field_defintions[name] = opt.info.annotation, opt.info
            else:
                continue

        if self.extra_allowed_fields:
            for name, info in self.extra_allowed_fields.items():
                if name not in field_defintions:
                    field_defintions[name] = info.annotation, info

        if field_defintions:
            extra_model_cls = ExtraModel if self.extra_strict_forbid else AllowedExtraModel
            self.extra_model = create_model(
                model_name="ExtraModel",
                __base__=extra_model_cls,
                **field_defintions
            )

    def rebuild_bet_opt(self, name: str, opt: BetOpt) -> Tuple[FieldInfo, FieldInfo]:
        """
        重新构建BetOpt

        Args:
            name (str): 字段名称
            opt (BetOpt): 字段元信息

        Returns:
            Tuple[FieldInfo,FieldInfo]: Between查询条件信息
        """
        min_opt = opt.replace(active="min")
        min_fieldinfo = FieldInfo.from_annotation(min_opt.info.annotation)
        min_fieldinfo.json_schema_extra = {"vo_opt": min_opt}
        max_opt = opt.replace(active="max")
        max_fieldinfo = FieldInfo.from_annotation(max_opt.info.annotation)
        max_fieldinfo.json_schema_extra = {"vo_opt": max_opt}
        return min_fieldinfo, max_fieldinfo

    def rebuild_field(self, name: str, info: FieldInfo) -> bool:
        """
        重置字段

        Args:
            name(str): 字段名称
            info(FieldInfo): 字段元信息

        Returns:
            bool: 是否支持重置
        """
        if self.context.include_fields and \
                name not in self.context.include_fields:
            return False
        if self.context.exclude_fields and \
                name in self.context.exclude_fields:
            return False
        flag = self.field_filter.filter(name, info)
        return flag


class FormSchemaFactory(AbcSchemaFactory):
    action = "form"
    model_config = strict_valid_config

    def validate_annotation(self, annotation: Type[BaseModel]) -> Optional[Type[BaseModel]]:
        pass


class PathSchemaFactory(AbcSchemaFactory):
    action = "path"
    model_config = query_valid_config

    def validate_annotation(self, annotation: Type[BaseModel]) -> Optional[Type[BaseModel]]:
        pass


class ArbitrarySchemaFactory(AbcSchemaFactory):
    model_config = query_valid_config

    def __init__(self):
        super().__init__()
        query_valid_config_copy = query_valid_config.copy()
        query_valid_config_copy.update({
            "arbitrary_types_allowed": True
        })
        self.model_config = query_valid_config_copy

    def validate_annotation(self, annotation: Type) -> Optional[Type[BaseEntity]]:
        bo_model = get_final_model(annotation)
        if issubclass(bo_model, BaseEntity):
            return bo_model
        else:
            return None
