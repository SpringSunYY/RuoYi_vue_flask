# -*- coding: utf-8 -*-
# @Author  : YY
# @FileName: __init__.py

import json
from typing import List, Optional, Tuple
from datetime import datetime

from ruoyi_common.utils import DateUtil, StringUtil
from ruoyi_generator.domain.entity import GenTable, GenTableColumn
from ruoyi_generator.mapper import gen_table_mapper, gen_table_column_mapper
from ruoyi_generator.util import GenUtils, to_underscore
from ruoyi_generator.config import GeneratorConfig


class GenTableService:
    def select_gen_table_list(self, gen_table: GenTable) -> Tuple[List[GenTable], int]:
        """
        查询代码生成表列表

        Args:
            gen_table (GenTable): 代码生成表对象

        Returns:
            Tuple[List[GenTable], int]: 代码生成表列表和总数
        """
        # 查询列表
        gen_tables = gen_table_mapper.select_list(gen_table)
        # 查询总数
        # 注意：这里需要根据实际需求实现总数查询逻辑
        total = len(gen_tables)
        return gen_tables, total

    def select_db_table_list(self, gen_table: GenTable) -> Tuple[List[GenTable], int]:
        """
        查询数据库表列表

        Args:
            gen_table (GenTable): 代码生成表对象

        Returns:
            Tuple[List[GenTable], int]: 数据库表列表和总数
        """
        # 查询列表
        gen_tables = gen_table_mapper.select_db_list(gen_table)
        # 查询总数
        # 注意：这里需要根据实际需求实现总数查询逻辑
        total = len(gen_tables)
        return gen_tables, total

    def select_gen_table_by_id(self, table_id: int) -> Optional[GenTable]:
        """
        根据ID查询代码生成表

        Args:
            table_id (int): 表ID

        Returns:
            Optional[GenTable]: 代码生成表对象
        """
        gen_table = gen_table_mapper.select_by_id(table_id)
        if gen_table:
            gen_table.columns = gen_table_column_mapper.select_list_by_table_id(table_id)
        return gen_table

    def select_gen_table_by_name(self, table_name: str) -> Optional[GenTable]:
        """
        根据表名查询代码生成表

        Args:
            table_name (str): 表名

        Returns:
            Optional[GenTable]: 代码生成表对象
        """
        return gen_table_mapper.select_by_table_name(table_name)

    def delete_gen_table_by_id(self, table_id: int):
        """
        根据ID删除代码生成表

        Args:
            table_id (int): 表ID
        """
        # 先删除字段信息
        gen_table_column_mapper.delete_by_table_id(table_id)
        # 再删除表信息
        gen_table_mapper.delete_by_id(table_id)

    def delete_gen_table_by_ids(self, table_ids: List[int]):
        """
        批量删除代码生成表

        Args:
            table_ids (List[int]): 表ID列表
        """
        for table_id in table_ids:
            # 先删除字段信息
            gen_table_column_mapper.delete_by_table_id(table_id)
            # 再删除表信息
            gen_table_mapper.delete_by_id(table_id)

    def import_gen_table(self, table_names: List[str]) -> int:
        """
        导入代码生成表

        Args:
            table_names (List[str]): 表名列表

        Returns:
            int: 导入的表数量
        """
        success_count = 0
        for table_name in table_names:
            # 检查表是否已存在
            if gen_table_mapper.exists_table(table_name):
                continue

            # 创建GenTable对象
            table = GenTable()

            # 设置默认值
            table.table_name = table_name
            clean_table_name = GenUtils.remove_table_prefix(
                table_name) if GeneratorConfig.auto_remove_pre else table_name
            table.class_name = to_underscore(clean_table_name)
            table.business_name = GenUtils.get_business_name(clean_table_name)
            table.package_name = GeneratorConfig.package_name
            # 使用配置中的 modelName 作为模块名
            table.module_name = GeneratorConfig.model_name

            # 获取表注释
            try:
                result = gen_table_mapper.select_db_table_comment_by_name(table_name)
                table.table_comment = result if result else table_name
            except:
                table.table_comment = table_name

            table.function_name = table.table_comment
            table.function_author = GeneratorConfig.author
            table.create_by = "admin"
            table.create_time = datetime.now()

            # 保存表信息
            table_id = gen_table_mapper.insert(table)
            if table_id > 0:
                # 保存列信息
                columns = gen_table_mapper.select_db_table_columns_by_name(table_name)
                if not columns:
                    print(f"警告：表 {table_name} 没有字段信息，可能表不存在或查询失败")
                else:
                    print(f"表 {table_name} 找到 {len(columns)} 个字段")
                for column in columns:
                    try:
                        column.table_id = table_id
                        column.create_by = "admin"
                        column.create_time = datetime.now()
                        # 确保 java_field 已设置
                        if not column.java_field:
                            column.java_field = GenUtils.to_camel_case(column.column_name)
                        gen_table_column_mapper.insert(column)
                    except Exception as e:
                        print(f"插入字段 {column.column_name} 失败: {e}")
                        continue
                success_count += 1
        return success_count

    def update_gen_table(self, gen_table: GenTable):
        """
        更新代码生成表

        Args:
            gen_table (GenTable): 代码生成表对象
        """
        print("更新代码生成表:", gen_table.columns)
        # 获取列信息
        columns = gen_table.columns
        if columns:
            # 处理列信息
            for column in columns:
                print("处理列信息:", column)
                # 确保column是GenTableColumn对象而不是dict
                column_obj = None
                if isinstance(column, dict):
                    # 直接使用字典数据创建对象，避免手动字段映射
                    # 前端传过来的已经是正确的字符串格式，直接使用
                    print("原始列数据:", column)

                    # 使用 model_validate 方法处理别名字段
                    column_obj = GenTableColumn.model_validate(column)
                    print("处理后列对象:", column_obj.model_dump())
                else:
                    column_obj = column

                # 设置表ID
                column_obj.table_id = gen_table.table_id
                column_obj.update_time = datetime.now()

                # 如果有column_id则更新，否则插入
                if hasattr(column_obj, 'column_id') and column_obj.column_id:
                    # 更新列信息
                    gen_table_column_mapper.update(column_obj)
                else:
                    # 插入列信息
                    column_obj.create_by = "admin"
                    column_obj.create_time = datetime.now()
                    gen_table_column_mapper.insert(column_obj)
        # 更新表信息
        gen_table.update_time = datetime.now()
        gen_table_mapper.update(gen_table)

    def synch_db(self, table_name: str):
        """
        同步数据库表结构

        Args:
            table_name (str): 表名
        """
        try:
            # 查询表信息
            gen_table = gen_table_mapper.select_by_table_name(table_name)
            if not gen_table:
                raise Exception(f"表{table_name}不存在")

            # 查询数据库表列信息
            db_columns = gen_table_mapper.select_db_table_columns_by_name(table_name)
            # 查询代码生成表列信息
            gen_columns = gen_table_column_mapper.select_list_by_table_id(gen_table.table_id)

            # 处理新增和更新的列
            for db_column in db_columns:
                exist_column = None
                for gen_column in gen_columns:
                    if db_column.column_name == gen_column.column_name:
                        exist_column = gen_column
                        break

                if exist_column:
                    # 更新列信息
                    exist_column.column_comment = db_column.column_comment
                    exist_column.column_type = db_column.column_type
                    exist_column.java_type = db_column.java_type
                    exist_column.java_field = db_column.java_field
                    exist_column.is_pk = db_column.is_pk
                    exist_column.is_increment = db_column.is_increment
                    exist_column.is_required = db_column.is_required
                    exist_column.update_by = "admin"
                    exist_column.update_time = datetime.now()
                    gen_table_column_mapper.update(exist_column)
                else:
                    # 新增列信息
                    db_column.table_id = gen_table.table_id
                    db_column.create_by = "admin"
                    db_column.create_time = datetime.now()
                    gen_table_column_mapper.insert(db_column)

            # 处理删除的列
            for gen_column in gen_columns:
                exist_column = False
                for db_column in db_columns:
                    if gen_column.column_name == db_column.column_name:
                        exist_column = True
                        break

                if not exist_column:
                    # 删除列信息
                    gen_table_column_mapper.delete_by_id(gen_column.column_id)
            
            return True
        except Exception as e:
            print(f"同步数据库失败: {e}")
            raise e

    def generator_code(self, table_name: str) -> bytes:
        """
        生成代码

        Args:
            table_name (str): 表名

        Returns:
            bytes: 生成的代码文件
        """
        # 查询表信息
        gen_table = gen_table_mapper.select_by_table_name(table_name)
        if not gen_table:
            raise Exception(f"表{table_name}不存在")

        # 查询列信息
        gen_table.columns = gen_table_column_mapper.select_list_by_table_id(gen_table.table_id)
        
        # 设置列的 list_index 属性
        GenUtils.set_column_list_index(gen_table)
        
        # 设置主键列
        pk_columns = [column for column in gen_table.columns if column.is_pk == '1']
        if pk_columns:
            gen_table.pk_column = pk_columns[0]
        else:
            gen_table.pk_column = None

        # 生成代码
        return GenUtils.generator_code(gen_table).getvalue()

    def batch_generator_code(self, table_names: List[str]) -> bytes:
        """
        批量生成代码

        Args:
            table_names (List[str]): 表名列表

        Returns:
            bytes: 生成的代码文件
        """
        gen_tables = []
        for table_name in table_names:
            # 查询表信息
            gen_table = gen_table_mapper.select_by_table_name(table_name)
            if gen_table:
                # 查询列信息
                gen_table.columns = gen_table_column_mapper.select_list_by_table_id(gen_table.table_id)
                # 设置列的 list_index 属性
                GenUtils.set_column_list_index(gen_table)
                # 设置主键列
                pk_columns = [column for column in gen_table.columns if column.is_pk == '1']
                if pk_columns:
                    gen_table.pk_column = pk_columns[0]
                else:
                    gen_table.pk_column = None
                gen_tables.append(gen_table)

        # 生成代码
        return GenUtils.batch_generator_code(gen_tables).getvalue()

    def preview_code(self, table_id: int) -> dict:
        """
        预览代码

        Args:
            table_id (int): 表ID

        Returns:
            dict: 预览代码
        """
        # 查询表信息
        gen_table = gen_table_mapper.select_by_id(table_id)
        if not gen_table:
            raise Exception(f"表ID{table_id}不存在")

        # 查询列信息
        gen_table.columns = gen_table_column_mapper.select_list_by_table_id(table_id)
        
        # 设置列的 list_index 属性
        GenUtils.set_column_list_index(gen_table)
        
        # 设置主键列
        pk_columns = [column for column in gen_table.columns if column.is_pk == '1']
        if pk_columns:
            gen_table.pk_column = pk_columns[0]
        else:
            gen_table.pk_column = None

        # 预览代码
        return GenUtils.preview_code(gen_table)

    def select_db_table_comment_by_name(self, table_name: str) -> Optional[str]:
        """
        根据表名查询数据库表注释

        Args:
            table_name (str): 表名

        Returns:
            Optional[str]: 表注释
        """
        try:
            result = gen_table_mapper.session.execute(
                text(
                    "SELECT table_comment FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = :table_name"),
                {"table_name": table_name}
            ).fetchone()
            return result[0] if result else None
        except Exception:
            return None


# 实例化Service
gen_table_service = GenTableService()
