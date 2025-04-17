import json
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.core.config import settings
from app.services.message import MessageService

router = APIRouter()


@router.post(settings.main_path + "/send")
async def send_message(
    request: Request,
    service: MessageService = Depends(MessageService),
):
    """处理模板消息推送 (POST 请求)"""
    client_ip = request.client.host
    body = await request.body()
    body = json.loads(body)

    required_keys = {"openid", "title", "content"}
    if not required_keys.issubset(body.keys()):
        return Response(
            status_code=400,
            content=json.dumps({"code": 400, "msg": "Missing parameters."}),
            media_type="application/json",
        )
    result = await service.send_message(
        client_ip=client_ip,
        openid=body["openid"],
        title=body["title"],
        content=body["content"],
        group=body["group"] if "group" in body else None,
    )
    return Response(
        content=json.dumps(result),
        media_type="application/json",
    )


@router.get(settings.main_path + "/message")
async def get_message_endpoint(
    message_id: str,
    service: MessageService = Depends(MessageService),
):
    """消息查询接口, 仅处理ID参数传递"""
    try:
        result = await service.get_message(message_id)
        return Response(
            content=json.dumps({"code": 200, "data": result}),
            media_type="application/json",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
