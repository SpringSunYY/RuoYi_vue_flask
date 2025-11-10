# -*- coding: utf-8 -*-
# @Author  : YY
# @FileName: ruoyi_generator.py

import json
import os
from typing import List
from zipfile import ZipFile
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
from ruoyi_common.utils import StringUtil
from ruoyi_common.constant import Constants

from ruoyi_generator.domain.entity import GenTable, GenTableColumn
from ruoyi_generator.mapper import gen_table_mapper, gen_table_column_mapper
from ruoyi_generator.util import GenUtils
from ruoyi_generator.config import GeneratorConfig
from datetime import datetime
from ruoyi_admin.ext import db
from sqlalchemy import text
from flask import Flask
from ruoyi_admin import create_app
from ruoyi_generator.mapper import gen_table_mapper
from ruoyi_generator.domain.entity import GenTable
from ruoyi_generator.config import GeneratorConfig
from ruoyi_common.utils import StringUtil
from ruoyi_generator.util import to_underscore


class RuoYiGenerator:
    def __init__(self):
        # 初始化模板引擎
        self.template_env = Environment(
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'vm')),
            autoescape=False  # 关闭自动转义，避免HTML转义字符
        )
        
    def get_template_data(self, table_id: int) -> dict:
        """
        获取模板数据
        
        Args:
            table_id (int): 表ID
            
        Returns:
            dict: 模板数据
        """
        # 查询表信息
        table = gen_table_mapper.select_by_id(table_id)
        if not table:
            raise Exception(f"表ID {table_id} 不存在")
        
        # 查询列信息
        columns = gen_table_column_mapper.select_list_by_table_id(table_id)
        table.columns = columns
        
        # 设置列的 list_index 属性
        from ruoyi_generator.util import GenUtils
        GenUtils.set_column_list_index(table)
        
        # 设置主键列
        pk_columns = [column for column in columns if column.is_pk == '1']
        if pk_columns:
            table.pk_column = pk_columns[0]
        
        # 设置其他属性
        if table.options:
            try:
                table.options = json.loads(table.options) if isinstance(table.options, str) else table.options
                table.tree_name = table.options.get('treeName')
                table.tree_code = table.options.get('treeCode')
                table.tree_parent_code = table.options.get('treeParentCode')
                # 从 options 中提取 parentMenuId
                if 'parentMenuId' in table.options:
                    table.parent_menu_id = table.options.get('parentMenuId')
            except Exception:
                pass
        
        # 强制使用前端模块名（modelName），而不是 Python 模块名
        # module_name 必须使用 modelName（test），不能使用 pythonModelName（ruoyi_test）
        # 如果 module_name 是空的、等于 python_model_name 或包含 python_model_name，强制替换为 model_name
        original_module_name = table.module_name
        if not table.module_name or table.module_name == GeneratorConfig.python_model_name or (table.module_name and GeneratorConfig.python_model_name in table.module_name):
            table.module_name = GeneratorConfig.model_name
            if original_module_name != table.module_name:
                print(f"警告：table.module_name 从 '{original_module_name}' 强制替换为 '{table.module_name}'（前端模块名）")
        
        # 设置模板数据
        data = {
            'table': table,
            'constants': Constants,
            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return data
    
    def generate_files(self, table_id: int) -> dict:
        """
        生成文件内容
        
        Args:
            table_id (int): 表ID
            
        Returns:
            dict: 生成的文件内容，key为文件路径，value为文件内容
        """
        # 获取模板数据
        data = self.get_template_data(table_id)
        table = data['table']
        
        # 获取所有模板文件
        template_files = self.get_template_files()
        
        # 生成文件
        generated_files = {}
        for template_file in template_files:
            try:
                # 渲染模板
                template = self.template_env.get_template(template_file)
                content = template.render(**data)
                
                # 生成文件名
                file_name = GenUtils.get_file_name(template_file, table)
                generated_files[file_name] = content
            except Exception as e:
                print(f"渲染模板 {template_file} 失败: {e}")
                continue
                
        return generated_files
    
    def get_template_files(self) -> List[str]:
        """
        获取模板文件列表
        
        Returns:
            List[str]: 模板文件列表
        """
        template_files = []
        vm_dir = os.path.join(os.path.dirname(__file__), 'vm')
        
        # 递归遍历vm目录下的所有.vm文件
        for root, dirs, files in os.walk(vm_dir):
            for file in files:
                if file.endswith('.vm'):
                    # 获取相对于vm目录的路径
                    rel_path = os.path.relpath(os.path.join(root, file), vm_dir)
                    template_files.append(rel_path.replace('\\', '/'))
                    
        return template_files
    
    def preview_code(self, table_id: int) -> dict:
        """
        预览代码
        
        Args:
            table_id (int): 表ID
            
        Returns:
            dict: 生成的代码
        """
        try:
            # 生成文件内容
            generated_files = self.generate_files(table_id)
            
            # 返回生成的代码
            return generated_files
        except Exception as e:
            print(f"预览代码失败: {e}")
            return {}
    
    def download_code(self, table_id: int) -> bytes:
        """
        下载代码
        
        Args:
            table_id (int): 表ID
            
        Returns:
            bytes: 生成的代码压缩包
        """
        # 生成文件内容
        generated_files = self.generate_files(table_id)
        
        # 创建ZIP文件
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            for file_path, content in generated_files.items():
                zip_file.writestr(file_path, content)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    def import_table(self, table_name: str) -> bool:
        """导入表"""
        try:
            # 检查表是否已存在
            if gen_table_mapper.exists_table(table_name):
                # 如果表已存在，直接同步字段信息
                from ruoyi_generator.service import GenTableService
                service = GenTableService()
                return service.synch_db(table_name)
            
            # 创建表信息
            table = GenTable()
            table.table_name = table_name
            
            # 获取表注释
            try:
                table_comment_result = db.session.execute(
                    text("SELECT table_comment FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = :table_name"),
                    {"table_name": table_name}
                ).fetchone()
                table.table_comment = table_comment_result[0] if table_comment_result and table_comment_result[0] else table_name
            except Exception as e:
                print(f"获取表注释失败: {e}")
                table.table_comment = table_name
            
            # 处理表名前缀
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
            
            # 插入表信息到数据库
            table_id = gen_table_mapper.insert(table)
            
            # 获取表列信息
            columns = gen_table_mapper.select_db_table_columns_by_name(table_name)
            # 即使没有列信息也继续处理
            if not columns:
                print(f"警告：未能获取到表 {table_name} 的列信息")
                
            for i, column in enumerate(columns or []):
                column.table_id = table_id
                column.sort = i + 1
                column.create_by = "admin"
                
                # 设置默认的字段属性
                if not column.java_type:
                    if column.column_type in ['int', 'integer', 'tinyint', 'smallint', 'mediumint']:
                        column.java_type = 'Integer'
                    elif column.column_type in ['bigint']:
                        column.java_type = 'Long'
                    elif column.column_type in ['float', 'double', 'decimal', 'numeric']:
                        column.java_type = 'BigDecimal'
                    elif column.column_type in ['date', 'datetime', 'timestamp']:
                        column.java_type = 'Date'
                    else:
                        column.java_type = 'String'
                
                if not column.java_field:
                    column.java_field = GenUtils.to_camel_case(column.column_name)
                
                if not column.html_type:
                    if column.column_type in ['date', 'datetime', 'timestamp']:
                        column.html_type = 'datetime'
                    elif column.column_type in ['text', 'longtext', 'mediumtext']:
                        column.html_type = 'textarea'
                    elif column.column_type in ['tinyint'] and column.column_name in ['status', 'is_delete', 'is_enabled']:
                        column.html_type = 'radio'
                    else:
                        column.html_type = 'input'
                
                if not column.query_type:
                    if column.column_type in ['varchar', 'char', 'text']:
                        column.query_type = 'LIKE'
                    else:
                        column.query_type = 'EQ'
                
                gen_table_column_mapper.insert(column)
            
            return True
        except Exception as e:
            print(f"导入表失败: {e}")
            return False
