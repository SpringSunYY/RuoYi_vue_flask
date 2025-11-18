import os
from typing import List
from jinja2 import Template
from ruoyi_common.utils import StringUtil
from ruoyi_generator.domain.entity import GenTable
from ruoyi_generator.config import GeneratorConfig
import zipfile
from io import BytesIO
from datetime import datetime
import re


def to_underscore(name: str) -> str:
    """
    将驼峰命名转换为下划线命名
    
    Args:
        name (str): 驼峰命名的字符串
        
    Returns:
        str: 下划线命名的字符串
    """
    # 处理 None 或非字符串类型
    if name is None:
        return ""
    if not isinstance(name, str):
        return str(name)
    # 在大写字母前添加下划线，然后转为小写
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def to_camel_case(name: str, pascal: bool = True) -> str:
    """
    将下划线命名或普通字符串转换为驼峰命名。

    - name = "schedule_info"  -> pascal=True  => "ScheduleInfo"
    - name = "schedule_info"  -> pascal=False => "scheduleInfo"
    - name = "ScheduleInfo"   -> pascal=True/False => "ScheduleInfo"/"scheduleInfo"
    """
    if name is None:
        return ""
    if not isinstance(name, str):
        name = str(name)
    if not name:
        return ""

    # 如果本身已经是驼峰（包含大写且不含下划线），直接按需调整首字母
    if "_" not in name and any(ch.isupper() for ch in name):
        base = name[0].upper() + name[1:]
    else:
        parts = [p for p in name.split("_") if p]
        if not parts:
            return ""
        base = "".join(p.lower().capitalize() for p in parts)

    return base if pascal else (base[0].lower() + base[1:] if base else base)


def capitalize_first(name: str) -> str:
    """
    将字符串首字母大写
    
    Args:
        name (str): 输入字符串
        
    Returns:
        str: 首字母大写的字符串
    """
    if name is None or not isinstance(name, str) or len(name) == 0:
        return ""
    return name[0].upper() + name[1:] if len(name) > 1 else name.upper()


def get_tree_column_index(column, all_columns):
    """
    计算树表中列的索引（排除主键列）
    
    Args:
        column: 当前列对象
        all_columns: 所有列的列表
        
    Returns:
        int: 列在树表中的索引
    """
    index = 0
    for col in all_columns:
        if col.is_list == '1' and not (col.is_pk == '1'):
            # 使用 column_id 或 column_name 来比较列对象
            if hasattr(column, 'column_id') and hasattr(col, 'column_id'):
                if col.column_id == column.column_id:
                    return index
            elif hasattr(column, 'column_name') and hasattr(col, 'column_name'):
                if col.column_name == column.column_name:
                    return index
            index += 1
    return 0


def get_filtered_columns(columns, filter_func):
    """
    过滤列并返回过滤后的列表
    
    Args:
        columns: 所有列的列表
        filter_func: 过滤函数，接受一个列对象，返回True表示保留
        
    Returns:
        list: 过滤后的列列表
    """
    return [col for col in columns if filter_func(col)]


class GenUtils:
    @staticmethod
    def get_file_name(template_file: str, table: GenTable) -> str:
        """
        根据模板文件名和表信息生成文件名
        
        Args:
            template_file (str): 模板文件名
            table (GenTable): 表信息
            
        Returns:
            str: 生成的文件名
        """
        # 标准化路径分隔符
        template_file = template_file.replace('\\', '/')
        
        # 移除.vm后缀
        base_name = template_file[:-3] if template_file.endswith('.vm') else template_file
        
        # 确定模块路径：后端代码使用 pythonModelName，前端代码使用 modelName
        if table.package_name:
            # 使用 package_name 作为路径（如 com.yy.test -> com/yy/test）
            module_path = table.package_name.replace('.', '/')
        else:
            # 如果 package_name 为空，使用 pythonModelName 作为后端模块名
            # 注意：这里只用于后端 Python 代码路径，前端代码路径在下面单独处理
            module_path = GeneratorConfig.python_model_name if hasattr(GeneratorConfig, 'python_model_name') else (table.module_name if table.module_name else 'ruoyi_generator')
        
        # 根据模板类型生成文件名和路径
        if 'py/entity.py' in template_file:
            # Entity文件放在 domain/entity/ 目录下，使用下划线命名法
            entity_name = to_underscore(table.class_name)
            return f"{module_path}/domain/entity/{entity_name}.py"
        elif 'py/controller.py' in template_file:
            # 使用下划线命名法
            controller_name = f"{to_underscore(table.class_name)}_controller"
            return f"{module_path}/controller/{controller_name}.py"
        elif 'py/service.py' in template_file:
            # 使用下划线命名法
            service_name = f"{to_underscore(table.class_name)}_service"
            return f"{module_path}/service/{service_name}.py"
        elif 'py/mapper.py' in template_file:
            # 使用下划线命名法
            mapper_name = f"{to_underscore(table.class_name)}_mapper"
            return f"{module_path}/mapper/{mapper_name}.py"
        elif 'py/po.py' in template_file:
            # PO文件放在 domain/po/ 目录下，使用下划线命名法
            po_name = f"{to_underscore(table.class_name)}_po"
            return f"{module_path}/domain/po/{po_name}.py"
        elif 'vue/index.vue' in template_file or 'vue/index-tree.vue' in template_file or 'vue/index-sub.vue' in template_file:
            # 无论是树表还是普通表，Vue文件名都是index.vue
            # 使用数据库中的 module_name（前端模块名）
            frontend_module = table.module_name if table.module_name else GeneratorConfig.model_name
            return f"vue/views/{frontend_module}/{table.business_name}/index.vue"
        elif 'js/api.js' in template_file:
            # 使用数据库中的 module_name（前端模块名）
            frontend_module = table.module_name if table.module_name else GeneratorConfig.model_name
            return f"vue/api/{frontend_module}/{table.business_name}.js"
        elif 'py/__init__.py' in template_file:
            # 模块根目录的 __init__.py
            return f"{module_path}/__init__.py"
        elif 'sql/menu.sql' in template_file:
            return f"sql/{table.business_name}_menu.sql"
        elif 'README.md' in template_file:
            return f"{table.business_name}_README.md"
        else:
            # 处理其他模板文件，保持原有目录结构
            filename = os.path.basename(base_name)
            if '.' not in filename:
                filename += '.py'  # 默认添加.py扩展名
            return filename

    @staticmethod
    def get_table_prefix() -> str:
        """
        获取表前缀
        
        Returns:
            str: 表前缀
        """
        return GeneratorConfig.table_prefix or ""

    @staticmethod
    def remove_table_prefix(table_name: str) -> str:
        """
        移除表前缀
        
        Args:
            table_name (str): 表名
            
        Returns:
            str: 移除前缀后的表名
        """
        prefix = GenUtils.get_table_prefix()
        if prefix and table_name.startswith(prefix):
            return table_name[len(prefix):]
        return table_name

    @staticmethod
    def table_to_class_name(table_name: str) -> str:
        """
        将表名转换为类名
        
        Args:
            table_name (str): 表名
            
        Returns:
            str: 类名
        """
        # 移除表前缀
        clean_table_name = GenUtils.remove_table_prefix(table_name)
        # 转换为驼峰命名
        return GenUtils.to_camel_case(clean_table_name)

    @staticmethod
    def get_business_name(table_name: str) -> str:
        """
        获取业务名
        
        Args:
            table_name (str): 表名
            
        Returns:
            str: 业务名
        """
        # 移除表前缀
        clean_table_name = GenUtils.remove_table_prefix(table_name)
        # 获取下划线分隔的第一部分
        return GenUtils.substring_before(clean_table_name, "_") if "_" in clean_table_name else clean_table_name

    @staticmethod
    def get_import_path(package_name: str, module_name: str, module_type: str, class_name: str = None) -> str:
        """
        生成导入路径
        
        Args:
            package_name (str): 包名，如 "com.yy.project" 或空字符串
            module_name (str): 前端模块名（从数据库读取，用于前端代码），但这里应该传入 pythonModelName
            module_type (str): 模块类型，如 "domain", "service", "mapper", "controller"
            class_name (str): 类名（可选，用于PO导入）
            
        Returns:
            str: 导入路径，Python包名保持点分隔格式
        """
        # Python 后端代码使用 pythonModelName，而不是前端模块名
        # 如果 package_name 为空，使用 pythonModelName 作为 Python 模块名
        if not package_name:
            # 使用 pythonModelName 作为 Python 模块名
            python_package = GeneratorConfig.python_model_name if hasattr(GeneratorConfig, 'python_model_name') else (module_name if module_name else 'ruoyi_generator')
        else:
            # Python导入路径使用点分隔，保持原样
            # 例如: "com.yy.project" -> "com.yy.project"
            python_package = package_name
        
        # 生成导入路径
        if module_type == "domain" and class_name:
            # PO 文件在 domain/po/ 目录下
            return f"{python_package}.domain.po"
        elif module_type == "domain":
            return f"{python_package}.domain.entity"
        else:
            return f"{python_package}.{module_type}"

    @staticmethod
    def to_camel_case(name: str) -> str:
        """
        将下划线命名转换为驼峰命名
        
        Args:
            name (str): 下划线命名
            
        Returns:
            str: 驼峰命名
        """
        if hasattr(StringUtil, 'to_camel_case'):
            return StringUtil.to_camel_case(name)
        # 如果StringUtil没有to_camel_case方法，则手动实现
        parts = name.split('_')
        if len(parts) == 1:
            return parts[0]
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])

    @staticmethod
    def substring_before(string: str, separator: str) -> str:
        """
        获取字符串中分隔符之前的部分
        
        Args:
            string (str): 输入字符串
            separator (str): 分隔符
            
        Returns:
            str: 分隔符之前的部分
        """
        if hasattr(StringUtil, 'substring_before'):
            return StringUtil.substring_before(string, separator)
        # 如果StringUtil没有substring_before方法，则手动实现
        if separator in string:
            return string.split(separator, 1)[0]
        return string

    @staticmethod
    def substring_after(string: str, separator: str) -> str:
        """
        获取字符串中分隔符之后的部分
        
        Args:
            string (str): 输入字符串
            separator (str): 分隔符
            
        Returns:
            str: 分隔符之后的部分
        """
        if hasattr(StringUtil, 'substring_after'):
            return StringUtil.substring_after(string, separator)
        # 如果StringUtil没有substring_after方法，则手动实现
        if separator in string:
            return string.split(separator, 1)[1]
        return ""
        
    @staticmethod
    def generator_code(table: GenTable) -> BytesIO:
        """
        生成代码
        
        Args:
            table (GenTable): 表信息
            
        Returns:
            BytesIO: 生成的代码文件
        """
        # 设置列的 list_index 属性
        GenUtils.set_column_list_index(table)
        
        # 设置主键列
        pk_columns = [column for column in table.columns if column.is_pk == '1']
        if pk_columns:
            table.pk_column = pk_columns[0]
        else:
            table.pk_column = None
        
        # 从 options 中解析 parentMenuId
        if table.options:
            import json
            try:
                if isinstance(table.options, str):
                    options_dict = json.loads(table.options)
                else:
                    options_dict = table.options
                # 从 options 中提取 parentMenuId 并设置到 table
                if 'parentMenuId' in options_dict:
                    table.parent_menu_id = options_dict.get('parentMenuId')
            except Exception as e:
                print(f"解析 options 字段出错: {e}")
        
        # 强制使用前端模块名（modelName），而不是 Python 模块名
        # module_name 必须使用 modelName（test），不能使用 pythonModelName（ruoyi_test）
        # 如果 module_name 是空的、等于 python_model_name 或包含 python_model_name，强制替换为 model_name
        original_module_name = table.module_name
        if not table.module_name or table.module_name == GeneratorConfig.python_model_name or (table.module_name and GeneratorConfig.python_model_name in table.module_name):
            table.module_name = GeneratorConfig.model_name
            if original_module_name != table.module_name:
                print(f"警告：table.module_name 从 '{original_module_name}' 强制替换为 '{table.module_name}'（前端模块名）")
        
        # 获取模板目录
        template_dir = os.path.join(os.path.dirname(__file__), 'vm')
        
        # 定义核心模板文件
        core_templates = [
            'py/entity.py.vm',
            'py/po.py.vm', 
            'py/controller.py.vm',
            'py/service.py.vm',
            'py/mapper.py.vm',
            'js/api.js.vm',
            'sql/menu.sql.vm'
        ]
        
        # 根据表类型添加相应的Vue模板
        if table.tpl_category == 'tree':
            core_templates.append('vue/index-tree.vue.vm')
        elif table.tpl_category == 'sub':
            core_templates.append('vue/index-sub.vue.vm')
        else:
            core_templates.append('vue/index.vue.vm')
        
        # 创建内存中的ZIP文件
        zip_buffer = BytesIO()
        
        # 确定模块路径，用于生成 __init__.py
        # 后端 Python 代码使用 pythonModelName，而不是前端模块名
        if table.package_name:
            module_path = table.package_name.replace('.', '/')
        else:
            # 使用 pythonModelName 作为后端模块路径
            module_path = GeneratorConfig.python_model_name if hasattr(GeneratorConfig, 'python_model_name') else (table.module_name if table.module_name else 'ruoyi_generator')
        
        # 收集需要生成 __init__.py 的目录和文件信息
        init_dirs = set()
        # 收集每个目录下的文件，用于生成导入语句
        dir_files = {}  # {dir_path: [file_info]}
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 跟踪已添加的文件名以避免重复
            added_files = set()
            
            # 首先生成模块根目录的 __init__.py
            init_template_path = os.path.join(template_dir, 'py/__init__.py.vm')
            if os.path.exists(init_template_path):
                try:
                    with open(init_template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
                    
                    # 准备模板上下文（单个表时，tables 为 None）
                    context = {
                        'table': table,
                        'tables': None,  # 单个表生成时，tables 为 None
                        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'underscore': to_underscore,
                        'get_import_path': GenUtils.get_import_path,
                        'get_tree_column_index': get_tree_column_index
                    }
                    
                    # 使用Jinja2渲染模板
                    template = Template(template_content)
                    rendered_content = template.render(**context)
                    
                    # 生成文件名
                    init_file_path = f"{module_path}/__init__.py"
                    
                    # 将渲染后的内容写入ZIP文件
                    if rendered_content.strip():
                        zip_file.writestr(init_file_path, rendered_content)
                        added_files.add(init_file_path)
                except Exception as e:
                    print(f"处理模块 __init__.py 模板时出错: {e}")
            
            # 处理每个核心模板文件
            for relative_path in core_templates:
                template_path = os.path.join(template_dir, relative_path)
                if os.path.exists(template_path):
                    # 读取模板内容
                    try:
                        with open(template_path, 'r', encoding='utf-8') as f:
                            template_content = f.read()
                            
                        # 准备模板上下文
                        # table.module_name 是从数据库读取的前端模块名（真正的模块名，用于权限、前端、SQL）
                        # GeneratorConfig.python_model_name 是 Python 模块名（只用于 Python 后端代码路径）
                        # 为树表准备过滤后的列列表
                        if 'index-tree.vue' in relative_path:
                            # 过滤出满足条件的列
                            list_cols = [col for col in table.columns if col.is_list and not (col.is_pk == '1') and getattr(col, 'list_index', None) is not None]
                            query_cols = [col for col in table.columns if col.is_query]
                            required_cols = [col for col in table.columns if col.is_required]
                        else:
                            list_cols = None
                            query_cols = None
                            required_cols = None
                        
                        context = {
                            'table': table,
                            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'underscore': to_underscore,  # 下划线命名工具
                            'capitalize_first': capitalize_first,  # 首字母大写工具
                            'to_camel_case': to_camel_case,  # 新增：驼峰命名工具
                            'get_import_path': GenUtils.get_import_path,  # 导入路径生成函数
                            'get_tree_column_index': get_tree_column_index,  # 树表列索引计算函数
                            'list_cols': list_cols,  # 树表的列表列
                            'query_cols': query_cols,  # 树表的查询列
                            'required_cols': required_cols  # 树表的必填列
                        }
                        
                        # 使用Jinja2渲染模板
                        template = Template(template_content)
                        # 如果是树表模板，打印列信息用于调试
                        if 'index-tree.vue' in relative_path:
                            print(f"[DEBUG] 渲染树表模板前，列信息:")
                            for col in table.columns:
                                list_idx = getattr(col, 'list_index', 'NOT_SET')
                                print(f"  - {col.column_name}: is_list={col.is_list}, is_pk={col.is_pk}, list_index={list_idx} (type={type(list_idx)})")
                        try:
                            rendered_content = template.render(**context)
                        except Exception as e:
                            import traceback
                            error_detail = traceback.format_exc()
                            print(f"[ERROR] 模板渲染失败: {relative_path}")
                            print(f"[ERROR] 错误信息: {str(e)}")
                            print(f"[ERROR] 详细堆栈:\n{error_detail}")
                            raise
                        
                        # 如果是 SQL 模板，恢复原始 module_name（虽然已经强制设置了，但为了安全）
                        if 'sql/menu.sql' in relative_path:
                            pass  # 已经强制设置为 model_name，不需要恢复
                        
                        # 生成文件名
                        output_file_name = GenUtils.get_file_name(relative_path, table)
                        
                        # 收集目录路径和文件信息，用于生成 __init__.py
                        # 跳过 sql 和 vue 目录，这些目录不需要 __init__.py
                        dir_path = os.path.dirname(output_file_name)
                        if dir_path and 'sql' not in dir_path and 'vue' not in dir_path:
                            init_dirs.add(dir_path)
                            # 同时收集父目录（但也要跳过 sql 和 vue）
                            parts = dir_path.split('/')
                            for i in range(1, len(parts)):
                                parent_dir = '/'.join(parts[:i])
                                if parent_dir and 'sql' not in parent_dir and 'vue' not in parent_dir:
                                    init_dirs.add(parent_dir)
                            
                            # 收集文件信息用于生成导入语句
                            file_name = os.path.basename(output_file_name)
                            file_base = os.path.splitext(file_name)[0]
                            
                            if dir_path not in dir_files:
                                dir_files[dir_path] = []
                            
                            # 根据文件类型确定导入的类名
                            if '/entity/' in output_file_name and '.py' in output_file_name:
                                # Entity 文件在 domain/entity/ 目录下
                                dir_files[dir_path].append(('entity', table.class_name, table))
                            elif '/po/' in output_file_name and '_po.py' in output_file_name:
                                # PO 文件在 domain/po/ 目录下
                                dir_files[dir_path].append(('po', f"{to_underscore(table.class_name)}_po", table))
                            elif '_service.py' in output_file_name:
                                dir_files[dir_path].append(('service', f"{to_underscore(table.class_name)}_service", table))
                            elif '_mapper.py' in output_file_name:
                                dir_files[dir_path].append(('mapper', f"{to_underscore(table.class_name)}_mapper", table))
                            elif '_controller.py' in output_file_name:
                                dir_files[dir_path].append(('controller', 'gen', table))
                        
                        # 检查渲染后的内容是否为空
                        if rendered_content.strip():
                            # 将渲染后的内容写入ZIP文件
                            zip_file.writestr(output_file_name, rendered_content)
                        else:
                            print(f"警告: 模板 {relative_path} 渲染后内容为空")
                    except Exception as e:
                        print(f"处理模板 {relative_path} 时出错: {e}")
            
            # 为每个目录生成 __init__.py 文件，使其成为完整的 Python 模块
            for dir_path in sorted(init_dirs):
                # 跳过模块根目录，因为已经在开始时生成
                if dir_path == module_path:
                    continue
                
                # 跳过 sql 和 vue 目录，这些目录不需要 __init__.py
                if 'sql' in dir_path or 'vue' in dir_path or dir_path.startswith('sql/') or dir_path.startswith('vue/'):
                    continue
                
                init_file_path = os.path.join(dir_path, '__init__.py').replace('\\', '/')
                
                # 生成 __init__.py 内容
                init_lines = ["# -*- coding: utf-8 -*-"]
                init_lines.append(f"# @Module: {dir_path}")
                init_lines.append("")
                
                # 特殊处理 controller 目录：参考 ruoyi_generator/controller/__init__.py 的格式
                if 'controller' in dir_path and dir_path.endswith('/controller'):
                    # 在 controller/__init__.py 中为每个 controller 创建蓝图
                    if dir_path in dir_files:
                        # 先导入 Blueprint
                        init_lines.append("from flask import Blueprint")
                        init_lines.append("")
                        
                        # 为每个 controller 创建蓝图
                        for file_type, class_name, table_info in dir_files[dir_path]:
                            if file_type == 'controller':
                                blueprint_name = to_underscore(table_info.class_name)
                                url_prefix = f"/{table_info.module_name}/{table_info.business_name}"
                                init_lines.append(f"{blueprint_name} = Blueprint('{blueprint_name}', __name__, url_prefix='{url_prefix}')")
                        
                        # 导入各个 controller 模块
                        init_lines.append("")
                        init_lines.append("")
                        for file_type, class_name, table_info in dir_files[dir_path]:
                            if file_type == 'controller':
                                controller_module_name = f"{to_underscore(table_info.class_name)}_controller"
                                init_lines.append(f"from . import {controller_module_name}")
                else:
                    # 其他目录正常生成导入语句
                    if dir_path in dir_files:
                        imports = []
                        for file_type, class_name, table_info in dir_files[dir_path]:
                            if file_type == 'entity':
                                # Entity 文件在 domain/entity/ 目录下，导入时使用文件名
                                entity_file_name = to_underscore(class_name)
                                imports.append(f"from .{entity_file_name} import {class_name}")
                            elif file_type == 'po':
                                # PO 文件在 domain/po/ 目录下，导入时使用文件名
                                po_file_name = class_name  # class_name 已经是 address_info_po
                                imports.append(f"from .{po_file_name} import {class_name}")
                            elif file_type == 'service':
                                imports.append(f"from .{class_name} import {class_name}")
                            elif file_type == 'mapper':
                                imports.append(f"from .{class_name} import {class_name}")
                        
                        if imports:
                            init_lines.extend(sorted(set(imports)))
                
                init_content = "\n".join(init_lines) + "\n"
                zip_file.writestr(init_file_path, init_content)
        
        zip_buffer.seek(0)
        return zip_buffer
        
    @staticmethod
    def batch_generator_code(tables: List[GenTable]) -> BytesIO:
        """
        批量生成代码
        
        Args:
            tables (List[GenTable]): 表列表
            
        Returns:
            BytesIO: 生成的代码文件
        """
        # 为每个表设置列的 list_index 属性和主键列
        for table in tables:
            GenUtils.set_column_list_index(table)
            # 设置主键列
            pk_columns = [column for column in table.columns if column.is_pk == '1']
            if pk_columns:
                table.pk_column = pk_columns[0]
            else:
                table.pk_column = None
            
            # 从 options 中解析 parentMenuId
            if table.options:
                import json
                try:
                    if isinstance(table.options, str):
                        options_dict = json.loads(table.options)
                    else:
                        options_dict = table.options
                    # 从 options 中提取 parentMenuId 并设置到 table
                    if 'parentMenuId' in options_dict:
                        table.parent_menu_id = options_dict.get('parentMenuId')
                except Exception as e:
                    print(f"解析 options 字段出错: {e}")
            
            # 强制使用前端模块名（modelName），而不是 Python 模块名
            # module_name 必须使用 modelName（test），不能使用 pythonModelName（ruoyi_test）
            if not table.module_name or table.module_name == GeneratorConfig.python_model_name or table.module_name.strip() == GeneratorConfig.python_model_name:
                table.module_name = GeneratorConfig.model_name
            # 额外检查：如果 module_name 等于 python_model_name，强制替换
            if table.module_name == GeneratorConfig.python_model_name:
                table.module_name = GeneratorConfig.model_name
        
        # 定义核心模板文件（每个表都会生成，但 __init__.py 只生成一次）
        core_templates = [
            'py/entity.py.vm',
            'py/po.py.vm', 
            'py/controller.py.vm',
            'py/service.py.vm',
            'py/mapper.py.vm',
            'js/api.js.vm',
            'sql/menu.sql.vm'
        ]
        
        # 创建内存中的ZIP文件
        zip_buffer = BytesIO()
        
        # 获取模板目录
        template_dir = os.path.join(os.path.dirname(__file__), 'vm')
        
        # 确定模块路径（使用第一个表的模块路径）
        if tables and len(tables) > 0:
            first_table = tables[0]
            if first_table.package_name:
                module_path = first_table.package_name.replace('.', '/')
            else:
                # 使用 pythonModelName 作为后端模块路径
                module_path = GeneratorConfig.python_model_name if hasattr(GeneratorConfig, 'python_model_name') else (first_table.module_name if first_table.module_name else 'ruoyi_generator')
        else:
            module_path = GeneratorConfig.python_model_name if hasattr(GeneratorConfig, 'python_model_name') else 'ruoyi_generator'
        
        # 收集需要生成 __init__.py 的目录和文件信息
        init_dirs = set()
        # 收集每个目录下的文件，用于生成导入语句 {dir_path: [(file_type, class_name, table)]}
        dir_files = {}
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 跟踪已添加的文件名以避免重复
            added_files = set()
            
            # 首先为模块根目录生成 __init__.py（只生成一次，使用第一个表的信息）
            if tables and len(tables) > 0:
                init_template_path = os.path.join(template_dir, 'py/__init__.py.vm')
                if os.path.exists(init_template_path):
                    try:
                        with open(init_template_path, 'r', encoding='utf-8') as f:
                            template_content = f.read()
                        
                        # 准备模板上下文（批量生成时，传入所有表）
                        # table.module_name 是从数据库读取的前端模块名（真正的模块名，用于权限、前端、SQL）
                        # GeneratorConfig.python_model_name 是 Python 模块名（只用于 Python 后端代码路径）
                        context = {
                            'table': first_table,  # 用于兼容模板中的 table 变量
                            'tables': tables,  # 传入所有表，用于循环注册所有蓝图
                            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'underscore': to_underscore,
                            'get_import_path': GenUtils.get_import_path,
                            'get_tree_column_index': get_tree_column_index
                        }
                        
                        # 使用Jinja2渲染模板
                        template = Template(template_content)
                        rendered_content = template.render(**context)
                        
                        # 生成文件名
                        init_file_path = f"{module_path}/__init__.py"
                        
                        # 将渲染后的内容写入ZIP文件（只写入一次）
                        if rendered_content.strip() and init_file_path not in added_files:
                            zip_file.writestr(init_file_path, rendered_content)
                            added_files.add(init_file_path)
                    except Exception as e:
                        print(f"处理模块 __init__.py 模板时出错: {e}")
            
            # 处理每个表
            for table in tables:
                # 根据表类型添加相应的Vue模板
                if table.tpl_category == 'tree':
                    current_templates = core_templates + ['vue/index-tree.vue.vm']
                elif table.tpl_category == 'sub':
                    current_templates = core_templates + ['vue/index-sub.vue.vm']
                else:
                    current_templates = core_templates + ['vue/index.vue.vm']
                
                # 处理每个核心模板文件
                for relative_path in current_templates:
                    # 跳过模块根目录的 __init__.py，因为已经在开始时生成
                    if relative_path == 'py/__init__.py.vm':
                        continue
                    
                    template_path = os.path.join(template_dir, relative_path)
                    if os.path.exists(template_path):
                        # 读取模板内容
                        try:
                            with open(template_path, 'r', encoding='utf-8') as f:
                                template_content = f.read()
                                
                            # 准备模板上下文
                            # table.module_name 是从数据库读取的前端模块名（真正的模块名，用于权限、前端、SQL）
                            # GeneratorConfig.python_model_name 是 Python 模块名（只用于 Python 后端代码路径）
                            # 为树表准备过滤后的列列表
                            if 'index-tree.vue' in relative_path:
                                list_cols = [col for col in table.columns if col.is_list and not (col.is_pk == '1') and getattr(col, 'list_index', None) is not None]
                                query_cols = [col for col in table.columns if col.is_query]
                                required_cols = [col for col in table.columns if col.is_required]
                            else:
                                list_cols = None
                                query_cols = None
                                required_cols = None
                            
                            context = {
                                'table': table,
                                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'underscore': to_underscore,  # 下划线命名工具
                                'capitalize_first': capitalize_first,  # 首字母大写工具
                                'to_camel_case': to_camel_case,  # 新增：驼峰命名工具
                                'get_import_path': GenUtils.get_import_path,  # 导入路径生成函数
                                'list_cols': list_cols,  # 树表的列表列
                                'query_cols': query_cols,  # 树表的查询列
                                'required_cols': required_cols  # 树表的必填列
                            }
                            
                            # 使用Jinja2渲染模板
                            template = Template(template_content)
                            # 如果是树表模板，打印列信息用于调试
                            if 'index-tree.vue' in relative_path:
                                print(f"[DEBUG] 批量渲染树表模板前，列信息:")
                                for col in table.columns:
                                    list_idx = getattr(col, 'list_index', 'NOT_SET')
                                    print(f"  - {col.column_name}: is_list={col.is_list}, is_pk={col.is_pk}, list_index={list_idx} (type={type(list_idx)})")
                            try:
                                rendered_content = template.render(**context)
                            except Exception as e:
                                import traceback
                                error_detail = traceback.format_exc()
                                print(f"[ERROR] 模板渲染失败: {relative_path} (表: {table.table_name})")
                                print(f"[ERROR] 错误信息: {str(e)}")
                                print(f"[ERROR] 详细堆栈:\n{error_detail}")
                                raise
                            
                            # 生成文件名
                            output_file_name = GenUtils.get_file_name(relative_path, table)
                            
                            # 收集目录路径和文件信息，用于生成 __init__.py
                            # 跳过 sql 和 vue 目录，这些目录不需要 __init__.py
                            dir_path = os.path.dirname(output_file_name)
                            if dir_path and 'sql' not in dir_path and 'vue' not in dir_path:
                                init_dirs.add(dir_path)
                                # 同时收集父目录（但也要跳过 sql 和 vue）
                                parts = dir_path.split('/')
                                for i in range(1, len(parts)):
                                    parent_dir = '/'.join(parts[:i])
                                    if parent_dir and 'sql' not in parent_dir and 'vue' not in parent_dir:
                                        init_dirs.add(parent_dir)
                                
                                # 收集文件信息用于生成导入语句
                                if dir_path not in dir_files:
                                    dir_files[dir_path] = []
                                
                                # 根据文件类型确定导入的类名
                                if '/entity/' in output_file_name and '.py' in output_file_name:
                                    # Entity 文件在 domain/entity/ 目录下
                                    dir_files[dir_path].append(('entity', table.class_name, table))
                                elif '/po/' in output_file_name and '_po.py' in output_file_name:
                                    # PO 文件在 domain/po/ 目录下
                                    dir_files[dir_path].append(('po', f"{to_underscore(table.class_name)}_po", table))
                                elif '_service.py' in output_file_name:
                                    dir_files[dir_path].append(('service', f"{to_underscore(table.class_name)}_service", table))
                                elif '_mapper.py' in output_file_name:
                                    dir_files[dir_path].append(('mapper', f"{to_underscore(table.class_name)}_mapper", table))
                                elif '_controller.py' in output_file_name:
                                    dir_files[dir_path].append(('controller', 'gen', table))
                            
                            # 检查是否已添加同名文件
                            if output_file_name in added_files:
                                # 为重复文件添加序号
                                name, ext = os.path.splitext(output_file_name)
                                counter = 1
                                new_name = f"{name}_{counter}{ext}"
                                while new_name in added_files:
                                    counter += 1
                                    new_name = f"{name}_{counter}{ext}"
                                output_file_name = new_name
                            
                            # 检查渲染后的内容是否为空
                            if rendered_content.strip():
                                # 将渲染后的内容写入ZIP文件
                                zip_file.writestr(output_file_name, rendered_content)
                                added_files.add(output_file_name)
                            else:
                                print(f"警告: 模板 {relative_path} 渲染后内容为空")
                        except Exception as e:
                            print(f"处理表 {table.table_name} 的模板 {relative_path} 时出错: {e}")
            
            # 为每个目录生成 __init__.py 文件，使其成为完整的 Python 模块
            for dir_path in sorted(init_dirs):
                # 跳过模块根目录，因为已经在开始时生成
                if dir_path == module_path:
                    continue
                
                # 跳过 sql 和 vue 目录，这些目录不需要 __init__.py
                if 'sql' in dir_path or 'vue' in dir_path or dir_path.startswith('sql/') or dir_path.startswith('vue/'):
                    continue
                
                init_file_path = os.path.join(dir_path, '__init__.py').replace('\\', '/')
                
                # 生成 __init__.py 内容
                init_lines = ["# -*- coding: utf-8 -*-"]
                init_lines.append(f"# @Module: {dir_path}")
                init_lines.append("")
                
                # 特殊处理 controller 目录：参考 ruoyi_generator/controller/__init__.py 的格式
                if 'controller' in dir_path and dir_path.endswith('/controller'):
                    # 在 controller/__init__.py 中为每个 controller 创建蓝图
                    if dir_path in dir_files:
                        # 先导入 Blueprint
                        init_lines.append("from flask import Blueprint")
                        init_lines.append("")
                        
                        # 为每个 controller 创建蓝图
                        for file_type, class_name, table_info in dir_files[dir_path]:
                            if file_type == 'controller':
                                blueprint_name = to_underscore(table_info.class_name)
                                url_prefix = f"/{table_info.module_name}/{table_info.business_name}"
                                init_lines.append(f"{blueprint_name} = Blueprint('{blueprint_name}', __name__, url_prefix='{url_prefix}')")
                        
                        # 导入各个 controller 模块
                        init_lines.append("")
                        init_lines.append("")
                        for file_type, class_name, table_info in dir_files[dir_path]:
                            if file_type == 'controller':
                                controller_module_name = f"{to_underscore(table_info.class_name)}_controller"
                                init_lines.append(f"from . import {controller_module_name}")
                else:
                    # 其他目录正常生成导入语句
                    if dir_path in dir_files:
                        imports = []
                        for file_type, class_name, table_info in dir_files[dir_path]:
                            if file_type == 'entity':
                                # Entity 文件在 domain/entity/ 目录下，导入时使用文件名
                                entity_file_name = to_underscore(class_name)
                                imports.append(f"from .{entity_file_name} import {class_name}")
                            elif file_type == 'po':
                                # PO 文件在 domain/po/ 目录下，导入时使用文件名
                                po_file_name = class_name  # class_name 已经是 address_info_po
                                imports.append(f"from .{po_file_name} import {class_name}")
                            elif file_type == 'service':
                                imports.append(f"from .{class_name} import {class_name}")
                            elif file_type == 'mapper':
                                imports.append(f"from .{class_name} import {class_name}")
                        
                        if imports:
                            init_lines.extend(sorted(set(imports)))
                
                init_content = "\n".join(init_lines) + "\n"
                zip_file.writestr(init_file_path, init_content)
        
        zip_buffer.seek(0)
        return zip_buffer
        
    @staticmethod
    def set_column_list_index(table: GenTable):
        """
        为表的列设置 list_index 属性，用于 Vue 模板中的 columns 数组索引
        
        Args:
            table (GenTable): 表信息
        """
        if not table.columns:
            return
        
        # 如果是树表，需要排除主键列
        is_tree = table.tpl_category == 'tree'
        print(f"[DEBUG] set_column_list_index: 表类型={table.tpl_category}, 是树表={is_tree}, 列数={len(table.columns)}")
        
        list_index = 0
        for column in table.columns:
            # 对于树表，只处理 is_list='1' 且不是主键的列
            # 对于普通表，处理所有 is_list='1' 的列
            if column.is_list == '1' or column.is_list == 1:
                if is_tree and (column.is_pk == '1' or column.is_pk == 1):
                    # 树表的主键列不设置 list_index（树表中主键列不显示在列表中）
                    # 设置为 None，但模板中会通过 not (column.is_pk == '1') 过滤掉
                    setattr(column, 'list_index', None)
                    print(f"[DEBUG] 树表主键列: {column.column_name}, is_list={column.is_list}, is_pk={column.is_pk}, list_index=None")
                    continue
                # 使用 setattr 动态添加属性
                setattr(column, 'list_index', list_index)
                print(f"[DEBUG] 设置列索引: {column.column_name}, is_list={column.is_list}, is_pk={column.is_pk}, list_index={list_index}")
                list_index += 1
            else:
                # 非列表列也设置 list_index 为 None，保持一致性
                setattr(column, 'list_index', None)
                print(f"[DEBUG] 非列表列: {column.column_name}, is_list={column.is_list}, list_index=None")

    @staticmethod
    def preview_code(table: GenTable) -> dict:
        """
        预览代码
        
        Args:
            table (GenTable): 表信息
            
        Returns:
            dict: 预览代码
        """
        # 设置列的 list_index 属性
        GenUtils.set_column_list_index(table)
        
        # 设置主键列
        pk_columns = [column for column in table.columns if column.is_pk == '1']
        if pk_columns:
            table.pk_column = pk_columns[0]
        else:
            table.pk_column = None
        
        # 从 options 中解析 parentMenuId
        if table.options:
            import json
            try:
                if isinstance(table.options, str):
                    options_dict = json.loads(table.options)
                else:
                    options_dict = table.options
                # 从 options 中提取 parentMenuId 并设置到 table
                if 'parentMenuId' in options_dict:
                    table.parent_menu_id = options_dict.get('parentMenuId')
            except Exception as e:
                print(f"解析 options 字段出错: {e}")
        
        # 强制使用前端模块名（modelName），而不是 Python 模块名
        # module_name 必须使用 modelName（test），不能使用 pythonModelName（ruoyi_test）
        # 如果 module_name 是空的、等于 python_model_name 或包含 python_model_name，强制替换为 model_name
        original_module_name = table.module_name
        if not table.module_name or table.module_name == GeneratorConfig.python_model_name or (table.module_name and GeneratorConfig.python_model_name in table.module_name):
            table.module_name = GeneratorConfig.model_name
            if original_module_name != table.module_name:
                print(f"警告：table.module_name 从 '{original_module_name}' 强制替换为 '{table.module_name}'（前端模块名）")
        
        # 获取模板目录
        template_dir = os.path.join(os.path.dirname(__file__), 'vm')
        
        # 存储预览代码的字典
        preview_data = {}
        
        # 定义需要预览的核心模板文件
        core_templates = [
            'py/entity.py.vm',
            'py/po.py.vm', 
            'py/controller.py.vm',
            'py/service.py.vm',
            'py/mapper.py.vm',
            'js/api.js.vm',
            'sql/menu.sql.vm'
        ]
        
        # 根据表类型添加相应的Vue模板，但预览时都使用index.vue.vm作为文件名
        if table.tpl_category == 'tree':
            core_templates.append('vue/index-tree.vue.vm')
        else:
            core_templates.append('vue/index.vue.vm')
        
        # 处理每个核心模板文件
        for relative_path in core_templates:
            template_path = os.path.join(template_dir, relative_path)
            if os.path.exists(template_path):
                # 读取模板内容
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template_content = f.read()
                        
                    # 准备模板上下文
                    # table.module_name 是从数据库读取的前端模块名（真正的模块名，用于权限、前端、SQL）
                    # GeneratorConfig.python_model_name 是 Python 模块名（只用于 Python 后端代码路径）
                    # 为树表准备过滤后的列列表
                    if 'index-tree.vue' in relative_path:
                        list_cols = [col for col in table.columns if col.is_list and not (col.is_pk == '1') and getattr(col, 'list_index', None) is not None]
                        query_cols = [col for col in table.columns if col.is_query]
                        required_cols = [col for col in table.columns if col.is_required]
                    else:
                        list_cols = None
                        query_cols = None
                        required_cols = None
                    
                    context = {
                        'table': table,
                        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'underscore': to_underscore,  # 下划线命名工具
                        'capitalize_first': capitalize_first,  # 首字母大写工具
                        'to_camel_case': to_camel_case,  # 新增：驼峰命名工具
                        'get_import_path': GenUtils.get_import_path,  # 导入路径生成函数
                        'list_cols': list_cols,  # 树表的列表列
                        'query_cols': query_cols,  # 树表的查询列
                        'required_cols': required_cols  # 树表的必填列
                    }
                    
                    # 使用Jinja2渲染模板
                    template = Template(template_content)
                    # 如果是树表模板，打印列信息用于调试
                    if 'index-tree.vue' in relative_path:
                        print(f"[DEBUG] 预览树表模板前，列信息:")
                        for col in table.columns:
                            list_idx = getattr(col, 'list_index', 'NOT_SET')
                            print(f"  - {col.column_name}: is_list={col.is_list}, is_pk={col.is_pk}, list_index={list_idx} (type={type(list_idx)})")
                    rendered_content = template.render(**context)
                    
                    # 存储渲染后的内容
                    preview_data[relative_path] = rendered_content
                except Exception as e:
                    # 如果渲染失败，存储错误信息
                    import traceback
                    error_detail = traceback.format_exc()
                    print(f"[ERROR] 模板渲染失败: {relative_path}")
                    print(f"[ERROR] 错误信息: {str(e)}")
                    print(f"[ERROR] 详细堆栈:\n{error_detail}")
                    preview_data[relative_path] = f"模板渲染失败: {str(e)}\n详细错误:\n{error_detail}"
            else:
                preview_data[relative_path] = "模板文件不存在"
        
        return preview_data
