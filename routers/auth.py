import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
import jwt
from bson import ObjectId

from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


# 请求模型
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


# 响应模型
class UserResponse(BaseModel):
    id: str
    username: str
    avatar_name: str
    email: str
    avatar: str
    badges: list[str] = []


class AuthResponse(BaseModel):
    success: bool
    data: dict


def get_db():
    """获取数据库实例"""
    from config.database import get_db as _get_db
    return _get_db()


def hash_password(password: str) -> str:
    """
    临时方案：直接存储明文密码（极度不安全，仅用于开发调试）。
    后续必须改回安全的哈希存储方案！
    """
    logger.warning("当前环境使用明文密码存储，仅用于临时开发调试，请尽快改为安全哈希")
    return password


def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    临时方案：明文比较密码。
    """
    return plain_password == stored_password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def user_to_dict(user: dict) -> dict:
    """将 MongoDB 用户文档转换为响应格式"""
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "avatar_name": user.get("avatar_name", user["username"]),
        "email": user["email"],
        "avatar": user.get("avatar_url", "https://i.pravatar.cc/100"),
        "badges": user.get("badges", []),
    }


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """用户注册"""
    db = get_db()
    users_collection = db["users"]

    # 检查用户名是否已存在
    if users_collection.find_one({"username": request.username}):
        logger.warning("注册失败: 用户名 %s 已存在", request.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否已存在
    if users_collection.find_one({"email": request.email}):
        logger.warning("注册失败: 邮箱 %s 已存在", request.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )

    # 创建新用户（临时明文密码存储）
    password_hash = hash_password(request.password)
    user_doc = {
        "username": request.username,
        # 显示用昵称，默认同 username
        "avatar_name": request.username,
        "email": request.email,
        "password_hash": password_hash,
        "avatar_url": "https://i.pravatar.cc/100",
        "badges": [],
        "bio": "",
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = users_collection.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    # 生成 token
    token = create_access_token({"sub": str(user_doc["_id"]), "username": request.username})

    logger.info("用户注册成功: %s (ID: %s)", request.username, result.inserted_id)

    return {
        "success": True,
        "data": {
            "user": user_to_dict(user_doc),
            "token": token,
        },
    }


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """用户登录"""
    db = get_db()
    users_collection = db["users"]

    # 查找用户（支持用户名或邮箱登录）
    user = users_collection.find_one({
        "$or": [
            {"username": request.username},
            {"email": request.username}
        ]
    })

    if not user:
        logger.warning("登录失败: 用户 %s 不存在", request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 验证密码
    if not verify_password(request.password, user["password_hash"]):
        logger.warning("登录失败: 用户 %s 密码错误", request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 生成 token
    token = create_access_token({"sub": str(user["_id"]), "username": user["username"]})

    logger.info("用户登录成功: %s (ID: %s)", user["username"], user["_id"])

    return {
        "success": True,
        "data": {
            "user": user_to_dict(user),
            "token": token,
        },
    }

