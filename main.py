import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pymongo import MongoClient
import uvicorn

from utils.logger import get_logger
from config.database import init_db
from routers import auth
from routers import profile
from routers import friends

load_dotenv()
logger = get_logger(__name__)

app = FastAPI()

# CORS 设置
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
mongo_uri = os.getenv("MONGO_URI")
try:
    client = MongoClient(mongo_uri)
    client.admin.command("ping")
    logger.info("MongoDB 连接成功")
    init_db(mongo_uri)
except Exception as exc:
    logger.error("MongoDB 连接失败: %s", exc)
    raise

# 注册路由
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(friends.router)


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)