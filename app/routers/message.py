import json
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Response
from aiomysql import Connection
from app.core.config import settings
from app.database.mysql import MySQL
from app.database.mongo import MongoDB
from app.core.dependencies import get_mysql, get_mongodb, get_mp
from app.services.mp import MPUtils

router = APIRouter()


@router.post(settings.main_path + "/send")
async def send_message(
    request: Request,
    conn: Connection = Depends(get_mysql),
    mongodb: MongoDB = Depends(get_mongodb),
    mp: MPUtils = Depends(get_mp),
):
    # 处理模板消息推送（POST 请求）
    client_ip = request.client.host
    body = await request.body()
    body = json.loads(body)
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    required_keys = {"openid", "title", "content"}
    if not required_keys.issubset(body.keys()):
        return Response(
            content=json.dumps({"code": 400, "msg": "Missing parameters."}),
            status_code=400,
            media_type="application/json",
        )
    mongo_result = await mongodb.insert(
        {
            "openid": body["openid"],
            "title": body["title"],
            "content": body["content"],
            "ip": client_ip,
            "date": time_now,
        }
    )
    # print(mongo_result)
    if "group" in body:
        group_list = await MySQL.get_group_member(
            conn=conn,
            openid=body["openid"],
            group_name=body["group"],
        )
        result = {"msg": "nobody in group."}
        for openid in group_list:
            result = await mp.send_message(
                openid=openid,
                title=body["title"],
                ip=client_ip,
                date=time_now,
                redirect_url=settings.main_path
                + "/weixin_msg/"
                + str(mongo_result["inserted_id"]),
            )
            print(result)
    else:
        result = await mp.send_message(
            openid=body["openid"],
            title=body["title"],
            ip=client_ip,
            date=time_now,
            redirect_url=settings.main_path
            + "/weixin_msg/"
            + str(mongo_result["inserted_id"]),
        )
    return Response(content=json.dumps(result), media_type="application/json")


@router.get(settings.main_path + "/message")
async def get_message(
    id: str,
    mongodb: MongoDB = Depends(get_mongodb),
):
    # 获取推送详细信息
    result = await mongodb.find_one({"_id": id})
    del result["openid"]
    return Response(content=json.dumps(result), media_type="application/json")
