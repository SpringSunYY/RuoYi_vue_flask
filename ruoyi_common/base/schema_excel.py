from dataclasses import dataclass, field
from typing import List, Literal

from openpyxl.styles import PatternFill, Alignment, Font
from pydantic import Field


def ExcelField(
        name: str,
        cell_type: Literal['numeric', 'string', 'image'] = "string",
        width: int = 16,
        height: int = 14,
        default: str = '',
        converter: str = '',
        prompt: str = '',
        combo: List = [],
        date_format: str = '',
        is_statistics: bool = False,
        background_color: str = 'FFFFFFFF',
        color: str = 'FF000000',
        align: str = 'left',
        action: Literal['import', 'export', 'both'] = 'both',
        dict_type: str = ''
):
    excel_access = ExcelAccess(
        name=name,
        cell_type=cell_type,
        width=width,
        height=height,
        default=default,
        converter=converter,
        prompt=prompt,
        date_format=date_format,
        combo=combo,
        is_statistics=is_statistics,
        background_color=background_color,
        color=color,
        align=align,
        action=action,
        dict_type=dict_type
    )
    return Field(excel_access=excel_access)


def ExcelFields(*accesses: "ExcelAccess"):
    return Field(excel_access=accesses)


@dataclass
class ExcelAccess:
    # 导出时在excel中排序
    sort: int = 0

    # 导出到Excel中的名字
    name: str = ''

    # 日期格式, 如: yyyy-MM-dd
    date_format: str = ''

    # 字典类型，请设置字典的type值 (如: sys_user_sex)
    dict_type: str = ''

    # 读取内容转表达式 (如: 0=男,1=女,2=未知)
    converter: str = ''

    # 分隔符，读取字符串组内容
    separators: str = ','

    # Decimal 精度 默认:False(默认不开启Decimal格式化)
    scale: bool = False

    # Decimal 舍入规则
    roundmode: str = ''

    # 导出时在excel中每个行的高度 单位为字符
    height: int = 14

    # 导出时在excel中每个列的宽 单位为字符
    width: int = 16

    # 文字后缀,如% 90 变成90%
    suffix: str = ''

    # 当值为空时,字段的默认值
    default: str = ''

    # 提示信息
    prompt: str = ''

    # 设置只能选择不能输入的列内容.
    combo: List = field(default_factory=list)

    # 另一个类中的属性名称,支持多级获取,以小数点隔开
    attr: str = ''

    # 是否自动统计数据,在最后追加一行统计数据总和
    is_statistics: bool = False

    # 导出类型（numeric 数字 string 字符串 image 图片）
    cell_type: Literal['numeric', 'string', 'image'] = 'string'

    # # 表头背景色
    # header_background_color: str = 'FFF2F2F2'

    # # 表头文字颜色
    # header_color: str = 'FF000000'

    # 单元格背景色
    background_color: str = 'FFFFFFFF'

    # 单元格文字颜色
    color: str = 'FF000000'

    # 导出字段对齐方式（left：默认；left：靠左；center：居中；right：靠右）
    align: Literal['left', 'center', 'right'] = 'left'

    # 自定义数据处理器
    # handler: str = ''

    # 自定义数据处理器参数
    # args: List = field(default_factory=list)

    # 字段类型（both：导出导入；export：仅导出；import：仅导入）
    action: Literal['import', 'export', 'both'] = 'both'

    val: str = field(default=None, init=False)

    def __post_init__(self):
        self._fill = PatternFill(
            start_color=self.background_color,
            end_color=self.background_color,
        )
        self._align = Alignment(
            horizontal=self.align,
            vertical='center',
            text_rotation=0,
            wrap_text=False,
            shrink_to_fit=False,
            indent=0
        )
        self._header_font = Font(
            bold=True,
            size=12
        )
        self._row_font = Font(
            size=12
        )

    @property
    def fill(self):
        return self._fill

    @property
    def alignment(self):
        return self._align

    @property
    def header_font(self):
        return self._header_font

    @property
    def row_font(self):
        return self._row_font
