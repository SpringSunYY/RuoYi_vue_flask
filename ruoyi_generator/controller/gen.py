from flask import request, send_file
from zipfile import ZipFile
from io import BytesIO

from ruoyi_common.base.model import AjaxResponse, TableResponse
from ruoyi_common.constant import HttpStatus
from ruoyi_common.descriptor.serializer import JsonSerializer
from ruoyi_common.descriptor.validator import QueryValidator, BodyValidator, PathValidator
from ruoyi_framework.descriptor.permission import HasPerm, PreAuthorize
from ruoyi_generator.controller import gen
from ruoyi_generator.domain.entity import GenTable
from ruoyi_generator.domain.po import GenTablePO, GenTableColumnPO
from ruoyi_generator.service import GenTableService
from ruoyi_generator.service.column_service import GenTableColumnService

gen_table_service = GenTableService()
gen_table_column_service = GenTableColumnService()


@gen.route('/list', methods=["GET"])
@QueryValidator(is_page=True)
@PreAuthorize(HasPerm('tool:gen:list'))
@JsonSerializer()
def gen_list(dto: GenTablePO):
    """查询代码生成列表"""
    gen_table = GenTable()
    # 转换PO到Entity对象，只复制存在的字段
    for attr in dto.model_fields.keys():
        if hasattr(gen_table, attr):
            setattr(gen_table, attr, getattr(dto, attr))

    tables, total = gen_table_service.select_gen_table_list(gen_table)
    return TableResponse(code=HttpStatus.SUCCESS, msg='查询成功', rows=tables, total=total)


@gen.route('/db/list', methods=["GET"])
@QueryValidator(is_page=True)
@PreAuthorize(HasPerm('tool:gen:list'))
@JsonSerializer()
def db_list(dto: GenTablePO):
    """查询数据库表列表"""
    gen_table = GenTable()
    # 转换PO到Entity对象，只复制存在的字段
    for attr in dto.model_fields.keys():
        if hasattr(gen_table, attr):
            setattr(gen_table, attr, getattr(dto, attr))

    tables, total = gen_table_service.select_db_table_list(gen_table)
    return TableResponse(code=HttpStatus.SUCCESS, msg='查询成功', rows=tables, total=total)


@gen.route('/<int:tableId>', methods=["GET"])
@PathValidator()
@PreAuthorize(HasPerm('tool:gen:query'))
@JsonSerializer()
def get_gen_table(tableId: int):
    """查询代码生成详细信息"""
    table = gen_table_service.select_gen_table_by_id(tableId)
    # 如果表存在但没有字段信息，则尝试从数据库同步
    columns, total = gen_table_column_service.select_gen_table_column_list_by_table_id(tableId)
    if not columns:
        # 尝试同步数据库结构
        gen_table_service.synch_db(table.table_name)
        # 再次查询字段信息
        columns, total = gen_table_column_service.select_gen_table_column_list_by_table_id(tableId)

    # 获取所有表名列表
    all_tables_result = gen_table_service.select_gen_table_list(GenTable())
    all_tables = []
    if all_tables_result:
        # 确保返回的是完整的表对象而不是仅表名
        all_tables = all_tables_result[0]

    return AjaxResponse.from_success(data={
        'info': table,
        'rows': columns,
        'tables': all_tables
    })


@gen.route('/', methods=['POST'])
@BodyValidator()
@PreAuthorize(HasPerm('tool:gen:add'))
@JsonSerializer()
def add_gen_table(dto: GenTablePO):
    """新增代码生成表"""
    gen_table = GenTable()
    # 转换PO到Entity对象，只复制存在的字段
    for attr in dto.model_fields.keys():
        if hasattr(gen_table, attr):
            setattr(gen_table, attr, getattr(dto, attr))

    # 实现新增逻辑
    table_id = gen_table_service.insert_gen_table(gen_table)
    if table_id > 0:
        return AjaxResponse.from_success(msg='新增成功')
    else:
        return AjaxResponse.from_error(msg='新增失败')


@gen.route('/importTable', methods=['POST'])
@PreAuthorize(HasPerm('tool:gen:import'))
@JsonSerializer()
def import_table():
    """导入表结构"""
    tables = request.args.get('tables')
    if not tables:
        return AjaxResponse.from_error(msg='参数错误')

    table_list = [table.strip() for table in tables.split(',') if table.strip()]
    if not table_list:
        return AjaxResponse.from_error(msg='参数错误')

    gen_table_service.import_gen_table(table_list)
    return AjaxResponse.from_success(msg='导入成功')


@gen.route('/<int:tableId>', methods=['PUT'])
@BodyValidator()
@PreAuthorize(HasPerm('tool:gen:edit'))
@JsonSerializer()
def update_gen_table(dto: GenTablePO):
    print(dto)
    """修改保存代码生成信息"""
    gen_table = GenTable()
    # 设置表ID
    gen_table.table_id = dto.table_id

    # 从请求数据中设置属性
    for attr in dto.model_fields.keys():
        if hasattr(gen_table, attr):
            setattr(gen_table, attr, getattr(dto, attr))
    
    # 处理 options 字段（包含树配置与菜单父节点）和 parentMenuId
    import json
    options_dict = {}
    
    # 如果 options 字段存在，先解析它
    if hasattr(dto, 'options') and dto.options:
        try:
            if isinstance(dto.options, str):
                options_dict = json.loads(dto.options)
            else:
                options_dict = dto.options.copy() if hasattr(dto.options, 'copy') else dto.options
        except Exception as e:
            print(f"解析 options 字段出错: {e}")
            options_dict = {}
    
    # 合并树配置（来自 dto 的 treeCode/treeParentCode/treeName）
    # 兼容：如果前端把树配置直接放在 dto 顶层，则这里写入 options
    if getattr(dto, 'tree_code', None):
        options_dict['treeCode'] = dto.tree_code
    if getattr(dto, 'tree_parent_code', None):
        options_dict['treeParentCode'] = dto.tree_parent_code
    if getattr(dto, 'tree_name', None):
        options_dict['treeName'] = dto.tree_name

    # 检查 params 中是否有 parentMenuId 或树配置（部分前端可能通过 params 传递）
    if hasattr(dto, 'params') and dto.params:
        if isinstance(dto.params, dict):
            if 'parentMenuId' in dto.params:
                options_dict['parentMenuId'] = dto.params.get('parentMenuId')
            if 'treeCode' in dto.params:
                options_dict['treeCode'] = dto.params.get('treeCode')
            if 'treeParentCode' in dto.params:
                options_dict['treeParentCode'] = dto.params.get('treeParentCode')
            if 'treeName' in dto.params:
                options_dict['treeName'] = dto.params.get('treeName')
    
    # 更新 options 字段（无论是否包含 parentMenuId，都要保存）
    if options_dict is not None:
        gen_table.options = json.dumps(options_dict, ensure_ascii=False)
        if 'parentMenuId' in options_dict:
            gen_table.parent_menu_id = options_dict.get('parentMenuId')
            print(f"设置 parentMenuId: {options_dict.get('parentMenuId')}, options: {gen_table.options}")

    # 特别处理columns字段
    if hasattr(dto, 'columns') and dto.columns is not None:
        print(dto.columns)
        # 前端传过来的已经是正确的字符串格式，直接使用
        gen_table.columns = dto.columns
    else:
        gen_table.columns = dto.columns

    gen_table_service.update_gen_table(gen_table)
    return AjaxResponse.from_success(msg='修改成功')


@gen.route('/<tableIds>', methods=['DELETE'])
@PathValidator()
@PreAuthorize(HasPerm('tool:gen:remove'))
@JsonSerializer()
def delete_gen_table(tableIds: str):
    """删除代码生成表"""
    try:
        table_ids = [int(id) for id in tableIds.split(',')]
        gen_table_service.delete_gen_table_by_ids(table_ids)
        return AjaxResponse.from_success(msg='删除成功')
    except Exception as e:
        return AjaxResponse.from_error(msg=f'删除失败: {str(e)}')


@gen.route('/preview/<int:tableId>', methods=["GET"])
@PathValidator()
@PreAuthorize(HasPerm('tool:gen:preview'))
@JsonSerializer()
def preview(tableId: int):
    """预览代码"""
    try:
        data = gen_table_service.preview_code(tableId)
        return AjaxResponse.from_success(data=data)
    except Exception as e:
        return AjaxResponse.from_error(msg=f'预览失败: {str(e)}')


@gen.route('/download/<table_name>', methods=["GET"])
@PathValidator()
@PreAuthorize(HasPerm('tool:gen:code'))
@JsonSerializer()
def download(table_name: str):
    """生成代码（下载方式）"""
    try:
        data = gen_table_service.generator_code(table_name)
        return send_file(
            BytesIO(data),  # 将bytes包装成BytesIO对象
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{table_name}.zip'
        )
    except Exception as e:
        return AjaxResponse.from_error(msg=f'生成失败: {str(e)}')


@gen.route('/genCode/<table_name>', methods=["GET"])
@PathValidator()
@PreAuthorize(HasPerm('tool:gen:code'))
@JsonSerializer()
def gen_code(table_name: str):
    """生成代码（自定义路径）"""
    try:
        data = gen_table_service.generator_code(table_name)
        return send_file(
            BytesIO(data),  # 将bytes包装成BytesIO对象
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{table_name}.zip'
        )
    except Exception as e:
        return AjaxResponse.from_error(msg=f'生成失败: {str(e)}')


@gen.route('/batchGenCode', methods=["GET"])
@PreAuthorize(HasPerm('tool:gen:code'))
@JsonSerializer()
def batch_gen_code():
    """批量生成代码"""
    try:
        tables = request.args.get('tables')
        if not tables:
            return AjaxResponse.from_error(msg='参数错误')

        table_list = [table.strip() for table in tables.split(',') if table.strip()]
        if not table_list:
            return AjaxResponse.from_error(msg='参数错误')

        # 生成代码
        data = gen_table_service.batch_generator_code(table_list)
        return send_file(
            BytesIO(data),  # 将bytes包装成BytesIO对象
            mimetype='application/zip',
            as_attachment=True,
            download_name='code.zip'
        )
    except Exception as e:
        return AjaxResponse.from_error(msg=f'批量生成失败: {str(e)}')


@gen.route('/synchDb/<table_name>', methods=["GET"])
@PreAuthorize(HasPerm('tool:gen:edit'))
@JsonSerializer()
def synch_db(table_name):
    """同步数据库"""
    # 检查表名是否有效
    if not table_name or table_name.lower() == 'null':
        return AjaxResponse.from_error(msg='表名不能为空')
    try:
        result = gen_table_service.synch_db(table_name)
        if result:
            return AjaxResponse.from_success(msg='同步成功')
        else:
            return AjaxResponse.from_error(msg='同步失败')
    except Exception as e:
        return AjaxResponse.from_error(msg=f'同步失败: {str(e)}')


@gen.route('/column/list', methods=["GET"])
@QueryValidator(is_page=True)
@PreAuthorize(HasPerm('tool:gen:list'))
@JsonSerializer()
def column_list(dto: GenTableColumnPO):
    """查询数据库表字段列表"""
    table_id = request.args.get('tableId')
    if table_id:
        columns, total = gen_table_column_service.select_gen_table_column_list_by_table_id(int(table_id))
    else:
        columns, total = [], 0
    return TableResponse(code=HttpStatus.SUCCESS, msg='查询成功', rows=columns, total=total)


@gen.route('/export', methods=["GET"])
@PreAuthorize(HasPerm('tool:gen:export'))
@JsonSerializer()
def export():
    """导出代码生成表数据"""
    try:
        tables, total = gen_table_service.select_gen_table_list(GenTable())
        return AjaxResponse.from_success(data=tables, msg='导出成功')
    except Exception as e:
        return AjaxResponse.from_error(msg=f'导出失败: {str(e)}')


@gen.route('/tableInfo/<table_name>', methods=["GET"])
@PathValidator()
@PreAuthorize(HasPerm('tool:gen:list'))
@JsonSerializer()
def get_table_info(table_name: str):
    """获取表信息"""
    try:
        if not gen_table_service.validate_table_name(table_name):
            return AjaxResponse.from_error(msg='表名格式不正确')

        table_info = gen_table_service.get_table_info(table_name)
        return AjaxResponse.from_success(data=table_info)
    except Exception as e:
        return AjaxResponse.from_error(msg=f'获取表信息失败: {str(e)}')
