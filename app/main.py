import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
import app.routers.wechat as wechat
import app.routers.message as message
from app.database.redis import Redis
from app.services.mp import MPUtils


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 创建MongoDB客户端连接
    app.state.mongodb_client = AsyncIOMotorClient(
        host=settings.mongo_host,
        port=settings.mongo_port,
        username=settings.mongo_username,
        password=settings.mongo_password,
    )

    # 创建Redis客户端连接
    app.state.redis_client = Redis()
    await app.state.redis_client.initialize()
    app.state.mp_instance = MPUtils()

    yield

    app.state.mongodb_client.close()
    await app.state.redis_client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(wechat.router)
app.include_router(message.router)


if __name__ == "__main__":
    load_dotenv()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("WEB_PORT", 80)))
