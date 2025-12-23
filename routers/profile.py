import os
from typing import Optional
from bson import ObjectId
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl, EmailStr

from config.database import get_db
from utils.logger import get_logger
from routers.auth import AuthResponse, user_to_dict, ALGORITHM, SECRET_KEY

logger = get_logger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=32)
    avatar_name: Optional[str] = Field(None, max_length=64)
    avatar: Optional[HttpUrl] = None  # 如需放宽校验，可改为 constr(regex=...) 或 Optional[str]
    email: Optional[EmailStr] = None


def require_user(authorization: str = Header(None)):
    """
    简单的 JWT 校验：从 Authorization: Bearer <token> 解出 user_id，并返回用户文档。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未授权")

    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 token")

    db = get_db()
    user = db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


@router.put("", response_model=AuthResponse)
async def update_profile(body: ProfileUpdate, current_user: dict = Depends(require_user)):
    """
    更新用户 profile（支持部分更新）：username、avatar_name、avatar
    """
    db = get_db()
    users = db["users"]
    updates = {}

    # username 唯一检查
    if body.username:
        exist = users.find_one({"username": body.username, "_id": {"$ne": current_user["_id"]}})
        if exist:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
        updates["username"] = body.username

    # avatar
    if body.avatar is not None:
        updates["avatar_url"] = str(body.avatar)

    # avatar_name：允许空，空则回退 username
    if body.avatar_name is not None:
        updates["avatar_name"] = body.avatar_name or updates.get("username") or current_user["username"]

    # email 唯一检查
    if body.email is not None:
        exist = users.find_one({"email": body.email, "_id": {"$ne": current_user["_id"]}})
        if exist:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")
        updates["email"] = body.email

    if not updates:
        return {"success": True, "data": {"user": user_to_dict(current_user)}}

    users.update_one({"_id": current_user["_id"]}, {"$set": updates})
    new_user = users.find_one({"_id": current_user["_id"]})
    return {"success": True, "data": {"user": user_to_dict(new_user)}}

