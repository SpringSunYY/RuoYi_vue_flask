# -*- coding: utf-8 -*-
# @Author  : YY

import os
import time
from flask import request, send_from_directory
from pydantic import Field
from typing_extensions import Annotated
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import NotFound

from ruoyi_common.config import RuoYiConfig
from ruoyi_common.constant import Constants
from ruoyi_common.descriptor.serializer import JsonSerializer
from ruoyi_common.descriptor.validator import FileUploadValidator, QueryValidator
from ruoyi_common.base.model import AjaxResponse
from ruoyi_common.utils import FileUploadUtil, FileUtil, StringUtil
from ... import reg


@reg.api.route('/common/download')
@QueryValidator()
@JsonSerializer()
def common_download(
    file_name:Annotated[str,Field(min_length=1,max_length=100)],
    delete:Annotated[bool,Field(annotations=bool,default=False)],
):
    file_path = RuoYiConfig().download_path + file_name
    download_name = time.time() * 1000 + file_name[file_name.index("_") + 1:]
    try:
        response = send_from_directory(
            directory=RuoYiConfig().download_path,
            path=file_name,
            as_attachment=True,
            download_name=download_name,
        )
        if delete:
            FileUtil.delete_file(file_path)
    except NotFound as e:
        return AjaxResponse.from_error("文件不存在")
    except Exception as e:
        return AjaxResponse.from_error("下载失败")
    return response


@reg.api.route('/profile/<path:resource>')
@JsonSerializer()
def profile_resource(resource:str):
    """
    通过 /profile/** 访问上传资源
    例如：/profile/uploads/dev/upload/2025/11/11/xxx.jpg
    """
    # 安全处理相对路径
    safe_path = resource.replace("..", "").lstrip("/\\")
    try:
        directory = os.path.dirname(safe_path) or "."
        filename = os.path.basename(safe_path)
        response = send_from_directory(
            directory=directory,
            path=filename,
            as_attachment=False,
            download_name=filename,
        )
    except NotFound:
        return AjaxResponse.from_error("文件不存在")
    except Exception:
        return AjaxResponse.from_error("读取文件失败")
    return response


@reg.api.route('/common/upload', methods=['POST'])
@FileUploadValidator()
@JsonSerializer()
def common_upload():
    file:FileStorage = request.files.get('file')
    if not file:
        return AjaxResponse.from_error("上传文件不能为空")
    file_name = FileUploadUtil.upload(file, RuoYiConfig().upload_path)
    url = request.host_url[:-1] + file_name
    new_file_name = FileUploadUtil.get_filename(file_name)
    original_filename = file.filename
    ajax_response = AjaxResponse.from_success()
    # 兼容前端组件字段（期待 fileName）
    setattr(ajax_response,"url",url)
    setattr(ajax_response,"fileName",file_name)
    setattr(ajax_response,"newFileName",new_file_name)
    setattr(ajax_response,"originalFilename",original_filename)
    return ajax_response


@reg.api.route('/common/uploads', methods=['POST'])
@FileUploadValidator()
@JsonSerializer()
def common_uploads():
    file_names = []
    urls = []
    new_file_names = []
    original_filenames = []
    if not request.files:
        return AjaxResponse.from_error("上传文件不能为空")
    for _,file in request.files.items():
        file_name = FileUploadUtil.upload(file, RuoYiConfig().upload_path)
        file_names.append(file_name)
        url = request.host_url[:-1] + file_name
        urls.append(url)
        new_file_name = FileUploadUtil.get_filename(file_name)
        new_file_names.append(new_file_name)
        original_filename = file.filename
        original_filenames.append(original_filename)
    ajax_response = AjaxResponse.from_success()
    # 兼容 camelCase
    setattr(ajax_response,"urls", ",".join(urls))
    setattr(ajax_response,"fileNames", ",".join(file_names))
    setattr(ajax_response,"newFileNames", ",".join(new_file_names))
    setattr(ajax_response,"originalFilenames", ",".join(original_filenames))
    return ajax_response


@reg.api.route('/common/download/resource')
@QueryValidator()
@JsonSerializer()
def common_download_resource(
    resource:Annotated[str,Field(annotation=str,min_length=1,max_length=100)]
):
    download_path = RuoYiConfig().download_path + StringUtil.substring_after(resource,Constants.RESOURCE_PREFIX)
    download_name = os.path.basename(download_path)
    try:
        response = send_from_directory(
            directory=RuoYiConfig().download_path,
            path=download_path,
            as_attachment=True,
            download_name=download_name,
            )
    except NotFound as e:
        return AjaxResponse.from_error("文件不存在")
    except Exception as e:
        return AjaxResponse.from_error("下载失败")
    return response
