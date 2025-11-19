# @Author  : YY

import os
from flask import Flask
from ruoyi_common.ruoyi.extension import FlaskRuoYi
from ruoyi_common.config import RuoYiConfig

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ruoyi = FlaskRuoYi()


def create_app():
    app = Flask(__name__)
    app.config.from_object(RuoYiConfig)

    # 初始化 ruoyi
    ruoyi.init_app(app, PROJECT_ROOT)

    # 初始化其他扩展
    from ruoyi_admin.ext import cors, fredis, lm, db
    cors.init_app(app)
    fredis.init_app(app)
    lm.init_app(app)
    db.init_app(app)

    # 注册代码生成模块
    from ruoyi_generator import init_app
    init_app(app)
    # 注册测试模块
    try:
        from ruoyi_test import init_app as test_init_app
        test_init_app(app)
        print("Test module registered successfully")
    except ImportError:
        print("测试模块未找到或未正确配置")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)