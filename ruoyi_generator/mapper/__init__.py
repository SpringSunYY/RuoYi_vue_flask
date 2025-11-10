# -*- coding: utf-8 -*-
# @Author  : YY
# @FileName: __init__.py

from typing import List, Optional
import json
from datetime import datetime
from dateutil import parser
from ruoyi_common.utils import StringUtil

from ruoyi_generator.domain.entity import GenTable, GenTableColumn
from ruoyi_admin.ext import db
from sqlalchemy import text
from ruoyi_generator.util import GenUtils, to_underscore
from ruoyi_generator.config import GeneratorConfig
from ruoyi_common.sqlalchemy.model import ColumnEntityList
from ruoyi_generator.domain.po import GenTablePo, GenTableColumnPo


class GenTableMapper:
    default_fields = {
        "table_id", "table_name", "table_comment", "sub_table_name", "sub_table_fk_name",
        "class_name", "tpl_category", "package_name", "module_name", "business_name",
        "function_name", "function_author", "gen_type", "gen_path", "options",
        "create_by", "create_time", "update_by", "update_time", "remark"
    }
    
    default_columns = ColumnEntityList(GenTablePo, default_fields)
    
    def select_list(self, gen_table: GenTable) -> List[GenTable]:
        """
        查询代码生成表列表
        
        Args:
            gen_table (GenTable): 代码生成表对象
            
        Returns:
            List[GenTable]: 代码生成表列表
        """
        try:
            criterions = []
            
            if gen_table.table_name:
                criterions.append(GenTablePo.table_name.like(f"%{gen_table.table_name}%"))
                
            if gen_table.table_comment:
                criterions.append(GenTablePo.table_comment.like(f"%{gen_table.table_comment}%"))
            
            stmt = db.select(*self.default_columns).where(*criterions)
            
            # 分页查询
            if hasattr(gen_table, 'page_num') and hasattr(gen_table, 'page_size') and gen_table.page_num and gen_table.page_size:
                offset = (gen_table.page_num - 1) * gen_table.page_size
                stmt = stmt.limit(gen_table.page_size).offset(offset)
            
            stmt = stmt.order_by(GenTablePo.table_id.desc())
            
            result = db.session.execute(stmt).all()
            
            tables = []
            for row in result:
                table = self.default_columns.cast(row, GenTable)
                # 解析options字段以设置tree相关属性
                if table.options:
                    try:
                        options_dict = json.loads(table.options)
                        table.tree_name = options_dict.get('treeName')
                        table.tree_code = options_dict.get('treeCode')
                        table.tree_parent_code = options_dict.get('treeParentCode')
                    except Exception:
                        pass
                tables.append(table)
                
            return tables
        except Exception as e:
            print(f"查询代码生成表列表出错: {e}")
            # 返回空列表而不是模拟数据
            return []

    def select_db_list(self, gen_table: GenTable) -> List[GenTable]:
        """
        查询数据库表列表
        
        Args:
            gen_table (GenTable): 代码生成表对象
            
        Returns:
            List[GenTable]: 数据库表列表
        """
        # 查询真实的数据库表信息
        try:
            # 查询所有表名、表注释、创建时间和更新时间，按创建时间倒序排列
            result = db.session.execute(text("""
                SELECT table_name, table_comment, create_time, update_time 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                ORDER BY create_time DESC
            """)).fetchall()
            
            tables = []
            for row in result:
                table_name = row[0]
                table_comment = row[1] if row[1] else table_name
                create_time = row[2] if len(row) > 2 else None
                update_time = row[3] if len(row) > 3 else None
                # 检查是否已导入
                exists_result = db.session.execute(
                    text("SELECT COUNT(1) FROM gen_table WHERE table_name = :table_name"),
                    {"table_name": table_name}
                ).fetchone()
                
                exists = exists_result[0] > 0 if exists_result else False
                if not exists:
                    
                    table = GenTable()
                    table.table_name = table_name
                    table.table_comment = table_comment
                    # 设置创建时间和更新时间
                    if create_time:
                        table.create_time = create_time
                    if update_time:
                        table.update_time = update_time
                    # 设置默认值，以便前端显示
                    clean_table_name = GenUtils.remove_table_prefix(table_name) if GeneratorConfig.auto_remove_pre else table_name
                    # 使用下划线命名法而不是驼峰命名法
                    table.class_name = to_underscore(clean_table_name)
                    table.package_name = GeneratorConfig.package_name
                    # 使用配置中的 modelName 作为模块名
                    table.module_name = GeneratorConfig.model_name
                    table.business_name = StringUtil.substring_after(clean_table_name, "_") if hasattr(StringUtil, 'substring_after') and "_" in clean_table_name else clean_table_name
                    table.function_name = table.business_name
                    table.function_author = GeneratorConfig.author
                    table.create_by = "admin"
                    tables.append(table)
            
            # 应用过滤条件
            filtered_tables = []
            for table in tables:
                # 表名过滤
                if gen_table.table_name and table.table_name.find(gen_table.table_name) == -1:
                    continue
                # 表注释过滤
                if gen_table.table_comment and table.table_comment.find(gen_table.table_comment) == -1:
                    continue
                filtered_tables.append(table)
            
            return filtered_tables
        except Exception as e:
            # 出现异常时返回空列表
            print(f"查询数据库表出错: {e}")
            # 返回空列表而不是模拟数据
            return []

    def select_by_id(self, table_id: int) -> Optional[GenTable]:
        """
        根据ID查询代码生成表
        
        Args:
            table_id (int): 表ID
            
        Returns:
            Optional[GenTable]: 代码生成表对象
        """
        try:
            stmt = db.select(*self.default_columns).where(GenTablePo.table_id == table_id)
            row = db.session.execute(stmt).first()
            
            if row:
                table = self.default_columns.cast(row, GenTable)
                # 解析options字段以设置tree相关属性
                if table.options:
                    try:
                        options_dict = json.loads(table.options)
                        table.tree_name = options_dict.get('treeName')
                        table.tree_code = options_dict.get('treeCode')
                        table.tree_parent_code = options_dict.get('treeParentCode')
                    except Exception:
                        pass
                return table
            return None
        except Exception as e:
            print(f"根据ID查询代码生成表出错: {e}")
            return None

    def select_by_table_name(self, table_name: str) -> Optional[GenTable]:
        """
        根据表名查询代码生成表
        
        Args:
            table_name (str): 表名
            
        Returns:
            Optional[GenTable]: 代码生成表对象
        """
        try:
            stmt = db.select(*self.default_columns).where(GenTablePo.table_name == table_name)
            row = db.session.execute(stmt).first()
            
            if row:
                table = self.default_columns.cast(row, GenTable)
                return table
            return None
        except Exception as e:
            print(f"根据表名查询代码生成表出错: {e}")
            return None

    def select_db_table_comment_by_name(self, table_name: str) -> Optional[str]:
        """
        根据表名查询数据库表注释
        
        Args:
            table_name (str): 表名
            
        Returns:
            Optional[str]: 表注释
        """
        try:
            result = db.session.execute(
                text("SELECT table_comment FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = :table_name"),
                {"table_name": table_name}
            ).fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"查询表注释出错: {e}")
            return None

    def exists_table(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name (str): 表名
            
        Returns:
            bool: 是否存在
        """
        try:
            result = db.session.execute(
                text("SELECT COUNT(1) FROM gen_table WHERE table_name = :table_name"),
                {"table_name": table_name}
            ).fetchone()
            return result[0] > 0 if result else False
        except Exception as e:
            print(f"检查表是否存在出错: {e}")
            return False

    def insert(self, gen_table: GenTable) -> int:
        """
        插入代码生成表
        
        Args:
            gen_table (GenTable): 代码生成表对象
            
        Returns:
            int: 插入的表ID
        """
        try:
            # 使用model_dump方法直接获取所有字段的值，使用下划线命名
            table_data = gen_table.model_dump(by_alias=False, exclude_none=True)
            
            # 移除不需要插入的字段
            exclude_fields = {'table_id', 'page_size', 'page_num', 'columns', 'pk_column', 'tree_name', 'tree_code', 'tree_parent_code'}
            for field in exclude_fields:
                table_data.pop(field, None)
            
            # 移除不需要插入的字段
            table_data.pop('update_time', None)
            
            # 确保必要的字段有默认值
            table_data.setdefault('create_by', 'admin')
            table_data.setdefault('update_by', 'admin')
            
            # 设置创建时间
            if 'create_time' not in table_data:
                table_data['create_time'] = datetime.now()
            
            # 使用SQLAlchemy ORM方式插入数据
            gen_table_po = GenTablePo(**table_data)
            db.session.add(gen_table_po)
            db.session.flush()
            
            table_id = gen_table_po.table_id
            db.session.commit()
            
            return table_id
        except Exception as e:
            db.session.rollback()
            print(f"插入代码生成表出错: {e}")
            return 0

    def update(self, gen_table: GenTable):
        """
        更新代码生成表
        
        Args:
            gen_table (GenTable): 代码生成表对象
        """
        try:
            # 使用model_dump方法直接获取所有字段的值，使用下划线命名
            table_data = gen_table.model_dump(by_alias=False, exclude_none=True)
            
            # 移除不需要更新的字段
            exclude_fields = {'table_id', 'page_size', 'page_num', 'columns', 'pk_column', 'tree_name', 'tree_code', 'tree_parent_code', 'parent_menu_id'}
            for field in exclude_fields:
                table_data.pop(field, None)
            
            table_data.pop('create_time', None)
            table_data.pop('create_by', None)
            
            # 确保 options 字段被正确更新（即使为空也要更新）
            if 'options' in table_data:
                # options 字段需要保留，即使可能是空字符串
                pass
            
            # 确保必要的字段有默认值
            table_data.setdefault('update_by', 'admin')
            
            # 使用ORM方式更新数据
            stmt = db.update(GenTablePo).where(GenTablePo.table_id == gen_table.table_id).values(**table_data)
            db.session.execute(stmt)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"更新代码生成表出错: {e}")

    def delete_by_id(self, table_id: int):
        """
        根据ID删除代码生成表
        
        Args:
            table_id (int): 表ID
        """
        try:
            stmt = db.delete(GenTablePo).where(GenTablePo.table_id == table_id)
            db.session.execute(stmt)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"根据ID删除代码生成表出错: {e}")
            raise e


    def select_db_table_columns_by_name(self, table_name: str) -> List[GenTableColumn]:
        """
        根据表名查询数据库表列信息
        
        Args:
            table_name (str): 表名
            
        Returns:
            List[GenTableColumn]: 表列信息列表
        """
        try:
            # 查询表的列信息
            result = db.session.execute(text("""
                SELECT 
                    column_name,
                    column_comment,
                    data_type,
                    is_nullable,
                    column_default,
                    column_key,
                    extra
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() AND table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name}).fetchall()
            
            columns = []
            for i, row in enumerate(result):
                column = GenTableColumn()
                column.column_name = row[0]
                column.column_comment = row[1] if row[1] else row[0]
                column.column_type = row[2]
                
                # 设置Java类型
                if row[2] in ['int', 'integer', 'tinyint', 'smallint', 'mediumint']:
                    column.java_type = 'Integer'
                elif row[2] in ['bigint']:
                    column.java_type = 'Long'
                elif row[2] in ['float', 'double', 'decimal', 'numeric']:
                    column.java_type = 'BigDecimal'
                elif row[2] in ['date', 'datetime', 'timestamp']:
                    column.java_type = 'Date'
                else:
                    column.java_type = 'String'
                
                # 使用 GenUtils.to_camel_case 方法转换字段名
                column.java_field = GenUtils.to_camel_case(row[0])
                column.is_pk = '1' if row[5] == 'PRI' else '0'
                column.is_increment = '1' if row[6] == 'auto_increment' else '0'
                column.is_required = '0' if row[3] == 'YES' else '1'
                column.is_insert = '1'
                column.is_edit = '1'
                column.is_list = '1'
                column.is_query = '1'
                column.query_type = 'EQ'
                column.html_type = 'input'
                column.sort = i + 1
                
                columns.append(column)
            
            return columns
        except Exception as e:
            print(f"查询表列信息出错: {e}")
            # 返回空列表而不是模拟数据
            return []


class GenTableColumnMapper:
    default_fields = {
        "column_id", "table_id", "column_name", "column_comment", "column_type",
        "java_type", "java_field", "is_pk", "is_increment", "is_required",
        "is_insert", "is_edit", "is_list", "is_query", "query_type",
        "html_type", "dict_type", "sort", "create_by", "create_time",
        "update_by", "update_time", "remark"
    }
    
    default_columns = ColumnEntityList(GenTableColumnPo, default_fields)
    
    def select_list_by_table_id(self, table_id: int) -> List[GenTableColumn]:
        """
        根据表ID查询代码生成表列列表
        
        Args:
            table_id (int): 表ID
            
        Returns:
            List[GenTableColumn]: 代码生成表列列表
        """
        try:
            stmt = db.select(*self.default_columns).where(GenTableColumnPo.table_id == table_id).order_by(GenTableColumnPo.sort)
            result = db.session.execute(stmt).all()
            
            columns = []
            for row in result:
                column = self.default_columns.cast(row, GenTableColumn)
                columns.append(column)
                
            return columns
        except Exception as e:
            print(f"根据表ID查询代码生成表列列表出错: {e}")
            return []

    def insert(self, gen_table_column: GenTableColumn) -> int:
        """
        插入代码生成表列
        
        Args:
            gen_table_column (GenTableColumn): 代码生成表列对象
            
        Returns:
            int: 插入的列ID
        """
        try:
            # 使用ORM方式插入数据，使用下划线命名
            column_data = gen_table_column.model_dump(by_alias=False, exclude_none=False)
            
            # 移除数据库表中不存在的字段
            column_data.pop('page_num', None)
            column_data.pop('page_size', None)
            
            # 确保布尔字段有默认值
            bool_fields = ['is_pk', 'is_increment', 'is_required', 'is_insert', 
                          'is_edit', 'is_list', 'is_query']
            for field in bool_fields:
                if field in column_data and column_data[field] is None:
                    column_data[field] = "1"
            
            # 移除不需要插入的字段
            column_data.pop('update_time', None)
            
            # 设置创建时间
            if 'create_time' not in column_data:
                column_data['create_time'] = datetime.now()
            
            gen_table_column_po = GenTableColumnPo(**column_data)
            db.session.add(gen_table_column_po)
            db.session.flush()
            
            column_id = gen_table_column_po.column_id
            db.session.commit()
            
            return column_id
        except Exception as e:
            db.session.rollback()
            print(f"插入代码生成表列出错: {e}")
            return 0

    def update(self, gen_table_column: GenTableColumn):
        """
        更新代码生成表列
        
        Args:
            gen_table_column (GenTableColumn): 代码生成表列对象
        """
        try:
            # 使用model_dump方法直接获取所有字段的值，使用下划线命名
            column_data = gen_table_column.model_dump(by_alias=False, exclude_none=False)
            
            # 移除不需要更新的字段
            column_data.pop('create_time', None)
            column_data.pop('create_by', None)
            
            # 移除数据库表中不存在的字段
            column_data.pop('page_num', None)
            column_data.pop('page_size', None)
            
            # 设置更新时间
            column_data.setdefault('update_time', datetime.now())
            
            # 使用ORM方式更新数据
            stmt = db.update(GenTableColumnPo).where(GenTableColumnPo.column_id == gen_table_column.column_id).values(**column_data)
            db.session.execute(stmt)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"更新代码生成表列出错: {e}")
            raise e

    def delete_by_table_id(self, table_id: int):
        """
        根据表ID删除代码生成表列
        
        Args:
            table_id (int): 表ID
        """
        try:
            stmt = db.delete(GenTableColumnPo).where(GenTableColumnPo.table_id == table_id)
            db.session.execute(stmt)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"根据表ID删除代码生成表列出错: {e}")
            raise e

    def delete_by_id(self, column_id: int):
        """
        根据ID删除代码生成表列
        
        Args:
            column_id (int): 列ID
        """
        try:
            stmt = db.delete(GenTableColumnPo).where(GenTableColumnPo.column_id == column_id)
            db.session.execute(stmt)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"根据ID删除代码生成表列出错: {e}")


# 实例化Mapper
gen_table_mapper = GenTableMapper()
gen_table_column_mapper = GenTableColumnMapper()
