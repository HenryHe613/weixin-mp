# -*- coding: utf-8 -*-
# app/routers/wechat.py

import hashlib
from fastapi import APIRouter, Depends, Request, Response

from aiomysql import Connection
from app.core.config import settings
from app.core.dependencies import get_mysql
from app.database.mysql import MySQL
from app.services.wechat import WechatService

router = APIRouter()


@router.get(settings.main_path)
async def verify_server(request: Request):
    """验证微信服务器有效性"""
    signature = request.query_params.get("signature", "")
    timestamp = request.query_params.get("timestamp", "")
    nonce = request.query_params.get("nonce", "")
    echostr = request.query_params.get("echostr", "")

    # 计算签名
    params = sorted([settings.verify_token, timestamp, nonce])
    sign_str = "".join(params)
    hash_str = hashlib.sha1(sign_str.encode()).hexdigest()

    if hash_str == signature:
        return Response(content=echostr)
    else:
        return Response(content="Verification Failed", status_code=403)


@router.post(settings.main_path)
async def handle_message(
    request: Request,
    service: WechatService = Depends(WechatService),
):
    """处理用户消息 (POST 请求)"""
    try:
        # 解析原始消息
        msg_type, from_user, to_user, content = service.parse_message_body(
            body=await request.body()
        )

        # 分发消息处理
        if msg_type == "text":
            reply = await service.process_text_message(
                from_user=from_user,
                content=content,
            )
        else:
            reply = "暂不支持此类型消息"

        # 构造响应
        return Response(
            content=service.generate_xml_response(to_user, from_user, reply),
            media_type="application/xml",
        )

    # except WeChatException as e:
    #     return Response(content=str(e), status_code=e.status_code)
    except Exception as e:
        print(f"消息处理异常: {str(e)}")
        return Response(content="服务暂时不可用", status_code=500)
