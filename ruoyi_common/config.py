# -*- coding: utf-8 -*-
# @Author  : YY

import os

from ruoyi_common.ruoyi.config import CONFIG_CACHE
from ruoyi_common.base.snippet import classproperty


class RuoYiConfig:
    """
    系统相关配置

    设计为类属性访问方式，与 Java 版 RuoYi 一致：
        RuoYiConfig.profile
        RuoYiConfig.upload_path
        RuoYiConfig.download_path
    """

    @classproperty
    def profile(cls) -> str:
        """
        基础配置路径，从配置缓存中实时读取，避免在模块导入时
        CONFIG_CACHE 还未初始化导致为 None 的问题。

        对应 app.yml 中的 ruoyi.profile，通常是一个绝对路径，
        与 Java 版 RuoYi 保持一致，例如：G:/ruoyi/uploadPath
        """
        return CONFIG_CACHE.get("ruoyi.profile", "")

    @classproperty
    def upload_path(cls) -> str:
        """
        获取上传路径

        Returns:
            str: 上传路径（profile/upload），与 Java 版 RuoYi 行为一致
        """
        # profile 一般为绝对路径，这里直接在其下拼接 upload 目录
        return os.path.join(cls.profile, "upload")

    @classproperty
    def download_path(cls) -> str:
        """
        获取下载路径

        Returns:
            str: 下载路径（profile/download），与 Java 版 RuoYi 行为一致
        """
        return os.path.join(cls.profile, "download")

    @classproperty
    def avatar_path(cls) -> str:
        """
        获取头像路径

        Returns:
            str: 头像路径（profile/avatar），与 Java 版 RuoYi 行为一致
        """
        return os.path.join(cls.profile, "avatar")

    @classproperty
    def import_path(cls) -> str:
        """
        获取导入路径

        Returns:
            str: 导入路径（profile/import），与 Java 版 RuoYi 行为一致
        """
        return os.path.join(cls.profile, "import")


