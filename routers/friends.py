from datetime import datetime
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from config.database import get_db
from utils.logger import get_logger
from routers.profile import require_user

logger = get_logger(__name__)
router = APIRouter(prefix="/api/friends", tags=["friends"])


class AddFriendRequest(BaseModel):
    friend_id: str = Field(..., description="目标用户的 ID")


class FriendItem(BaseModel):
    id: str
    name: str
    avatar: str
    lastMessage: str
    online: bool
    unread: int
    lastMessageTime: Optional[datetime] = None
    status: Optional[str] = None


class FriendsResponse(BaseModel):
    success: bool
    data: List[FriendItem]


def _to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的用户 ID")


@router.post("/add", response_model=FriendsResponse)
async def add_friend(body: AddFriendRequest, current_user: dict = Depends(require_user)):
    """
    添加好友：直接建立 accepted 关系，使双方列表都可见。
    """
    db = get_db()
    users = db["users"]
    friendships = db["friendships"]

    # 尝试查找目标用户：先尝试 ObjectId，失败则尝试 username
    target_user = None
    try:
        target_user = users.find_one({"_id": ObjectId(body.friend_id)})
    except Exception:
        pass

    if not target_user:
        target_user = users.find_one({"username": body.friend_id})

    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    target_id = target_user["_id"]

    if target_id == current_user["_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能添加自己为好友")

    # 检查是否已是好友
    exist = friendships.find_one({
        "$or": [
            {"user_id": current_user["_id"], "friend_id": target_id},
            {"user_id": target_id, "friend_id": current_user["_id"]},
        ]
    })
    if exist:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已是好友或请求已存在")

    now = datetime.utcnow()
    friendships.insert_one({
        "user_id": current_user["_id"],
        "friend_id": target_id,
        "status": "accepted",
        "created_at": now,
        "updated_at": now,
    })

    # 返回当前用户的好友列表
    return await list_friends(current_user)  # type: ignore


def _friend_item(friend_user: dict) -> FriendItem:
    return FriendItem(
        id=str(friend_user["_id"]),
        name=friend_user.get("avatar_name") or friend_user.get("username"),
        avatar=friend_user.get("avatar_url", "https://i.pravatar.cc/100"),
        lastMessage=friend_user.get("last_message", ""),  # 占位，可后续替换为真实消息摘要
        online=friend_user.get("is_online", False),       # 若无实时状态，默认 False
        unread=int(friend_user.get("unread", 0)),
        lastMessageTime=friend_user.get("last_message_time"),
        status=friend_user.get("status", "active"),
    )


@router.get("", response_model=FriendsResponse)
async def list_friends(current_user: dict = Depends(require_user)):
    """
    获取好友列表。按 updated_at desc 排序。
    """
    db = get_db()
    users = db["users"]
    friendships = db["friendships"]

    relations = friendships.find({
        "$or": [
            {"user_id": current_user["_id"]},
            {"friend_id": current_user["_id"]},
        ],
        "status": "accepted",
    }).sort("updated_at", -1)

    friend_ids = []
    for rel in relations:
        if rel["user_id"] == current_user["_id"]:
            friend_ids.append(rel["friend_id"])
        else:
            friend_ids.append(rel["user_id"])

    if not friend_ids:
        return {"success": True, "data": []}

    friends_cursor = users.find({"_id": {"$in": friend_ids}})
    friends_map = {doc["_id"]: doc for doc in friends_cursor}

    items = []
    for fid in friend_ids:
        friend_user = friends_map.get(fid)
        if friend_user:
            items.append(_friend_item(friend_user))

    return {"success": True, "data": items}
