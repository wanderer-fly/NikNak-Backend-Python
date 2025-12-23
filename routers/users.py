from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from config.database import get_db
from routers.profile import require_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/search")
async def search_user(q: str, current_user: dict = Depends(require_user)):
    """
    根据 ID 或用户名精确查找用户
    """
    db = get_db()
    users = db["users"]

    query_parts = [{"username": q}]
    if ObjectId.is_valid(q):
        query_parts.append({"_id": ObjectId(q)})

    user = users.find_one({"$or": query_parts})

    if not user or user["_id"] == current_user["_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该用户")

    return {
        "success": True,
        "data": {
            "id": str(user["_id"]),
            "username": user["username"],
            "avatar_name": user.get("avatar_name", user["username"]),
            "avatar": user.get("avatar_url", "https://i.pravatar.cc/100")
        }
    }