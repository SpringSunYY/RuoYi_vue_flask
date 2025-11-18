# -*- coding: utf-8 -*-
# @Author  : shaw-lee

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
from ruoyi_common.descriptor.validator import FileValidator, QueryValidator
from ruoyi_common.base.model import AjaxResponse, MultiFile
from ruoyi_common.utils import FileUploadUtil, FileUtil, StringUtil
from ... import reg


@reg.api.route('/common/download')
@QueryValidator()
@JsonSerializer()
def common_download(
        file_name: Annotated[str, Field(min_length=1, max_length=100)],
        delete: Annotated[bool, Field(annotations=bool, default=False)],
):
    file_path = RuoYiConfig.download_path + file_name
    download_name = time.time() * 1000 + file_name[file_name.index("_") + 1:]
    try:
        response = send_from_directory(
            directory=RuoYiConfig.download_path,
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


@reg.api.route('/common/upload', methods=['POST'])
@FileValidator()
@JsonSerializer()
def common_upload(file: MultiFile):
    file: FileStorage = file.one()
    file_name = FileUploadUtil.upload(file, RuoYiConfig.upload_path)
    url = request.host_url[:-1] + file_name
    new_file_name = FileUploadUtil.get_filename(file_name)
    original_filename = file.filename
    ajax_response = AjaxResponse.from_success()
    # 为了兼容若依 Vue 前端，这里的字段名与 Java 版保持一致（驼峰命名）
    setattr(ajax_response, "url", url)
    setattr(ajax_response, "fileName", file_name)
    setattr(ajax_response, "newFileName", new_file_name)
    setattr(ajax_response, "originalFilename", original_filename)
    return ajax_response


@reg.api.route('/common/uploads', methods=['POST'])
@FileValidator()
@JsonSerializer()
def common_uploads(files: MultiFile):
    file_names = []
    urls = []
    new_file_names = []
    original_filenames = []
    for _, file in files.items():
        file_name = FileUploadUtil.upload(file, RuoYiConfig.upload_path)
        file_names.append(file_name)
        url = request.host_url[:-1] + file_name
        urls.append(url)
        new_file_name = FileUploadUtil.get_filename(file_name)
        new_file_names.append(new_file_name)
        original_filename = file.filename
        original_filenames.append(original_filename)
    ajax_response = AjaxResponse.from_success()
    # 多文件上传字段命名也与若依保持一致
    setattr(ajax_response, "urls", ",".join(urls))
    setattr(ajax_response, "fileNames", ",".join(file_names))
    setattr(ajax_response, "newFileNames", ",".join(new_file_names))
    setattr(ajax_response, "originalFilenames", ",".join(original_filenames))
    return ajax_response


@reg.api.route('/common/download/resource')
@QueryValidator()
@JsonSerializer()
def common_download_resource(
        resource: Annotated[str, Field(annotation=str, min_length=1, max_length=100)]
):
    download_path = RuoYiConfig.download_path + StringUtil.substring_after(resource, Constants.RESOURCE_PREFIX)
    download_name = os.path.basename(download_path)
    try:
        response = send_from_directory(
            directory=RuoYiConfig.download_path,
            path=download_path,
            as_attachment=True,
            download_name=download_name,
        )
    except NotFound as e:
        return AjaxResponse.from_error("文件不存在")
    except Exception as e:
        return AjaxResponse.from_error("下载失败")
    return response


@reg.api.route(f"{Constants.RESOURCE_PREFIX}/<path:resource>")
def common_profile_resource(resource: str):
    """
    静态资源访问：
    将 /profile/** 映射到配置的 profile 物理目录下，与 Java 版若依保持一致。

    例如：
    ruoyi.profile = G:/ruoyi/uploadPath
    URL:  /profile/upload/2025/11/18/xxx.jpg
    实际: G:/ruoyi/uploadPath/upload/2025/11/18/xxx.jpg
    """
    try:
        return send_from_directory(
            directory=RuoYiConfig.profile,
            path=resource,
        )
    except NotFound:
        return AjaxResponse.from_error("文件不存在")
