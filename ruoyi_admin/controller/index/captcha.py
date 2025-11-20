# -*- coding: utf-8 -*-
# @Author  : YY

import base64
import random
import string, uuid
from captcha.image import ImageCaptcha
from io import BytesIO

from ruoyi_common.base.model import AjaxResponse
from ruoyi_common.constant import Constants
from ruoyi_common.descriptor.serializer import JsonSerializer
from ruoyi_admin.ext import redis_cache
from ruoyi_system.service import SysConfigService
from ... import reg


@reg.api.route("/captchaImage")
@JsonSerializer()
def index_captcha_image():
    """
    生成验证码图片
    :return:
    """
    captchaOnOff = SysConfigService.select_captcha_on_off()
    if not captchaOnOff:
        return AjaxResponse.from_success()
    ImageCaptcha.character_rotate = (-15, 15)
    ImageCaptcha.character_warp_dx = (0.1, 0.1)
    ImageCaptcha.character_warp_dy = (0.1, 0.1)
    ImageCaptcha.word_offset_dx = 0.1
    ImageCaptcha.word_space_probability = 0
    image = ImageCaptcha(
        width=160,
        height=60,
        font_sizes=[42, 45, 48]
    )
    wait_letters = string.ascii_letters + string.digits
    exclude_letters = "oO0iIl1"
    sample_letters = [i for i in wait_letters if i not in exclude_letters]
    code = ''.join(random.sample(sample_letters, 4))
    uuid_str = uuid.uuid4().hex
    verifyKey = Constants.CAPTCHA_CODE_KEY + uuid_str
    redis_cache.set(verifyKey, code, ex=Constants.CAPTCHA_EXPIRATION * 60)

    byte_buffer = BytesIO()
    try:
        image.write(code, byte_buffer)
    except Exception as e:
        return AjaxResponse.from_error(str(e))
    byte_image = byte_buffer.getvalue()
    ajax_response = AjaxResponse.from_success()
    ajax_response.uuid = uuid_str
    ajax_response.img = str(base64.b64encode(byte_image), encoding="utf-8")
    ajax_response.captchaOnOff = captchaOnOff
    return ajax_response
