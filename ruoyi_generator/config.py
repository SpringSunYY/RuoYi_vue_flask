# -*- coding: utf-8 -*-
# @Author  : YY
# @FileName: config.py

import os
import yaml


class GeneratorConfig:
    # 作者
    author = "YY"
    
    # 默认前端模块名（用于前端代码路径和SQL component）
    model_name = "test"
    
    # 默认Python模块名（用于后端代码路径）
    python_model_name = "ruoyi_test"
    
    # 默认包名
    package_name = "com.yy.project"
    
    # 自动移除表前缀
    auto_remove_pre = True
    
    # 表前缀
    table_prefix = "sys_"
    
    # 读取配置文件
    config_file = os.path.join(os.path.dirname(__file__), "config", "generator.yml")
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.load(f, Loader=yaml.FullLoader)
            gen_config = config_data.get("gen", {})
            
            author = gen_config.get("author", author)
            model_name = gen_config.get("modelName", model_name)
            python_model_name = gen_config.get("pythonModelName", python_model_name)
            package_name = gen_config.get("packageName", package_name)
            auto_remove_pre = gen_config.get("autoRemovePre", auto_remove_pre)
            table_prefix = gen_config.get("tablePrefix", table_prefix)