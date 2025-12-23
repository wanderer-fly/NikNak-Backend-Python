from pymongo.database import Database
from pymongo import MongoClient
import os

_client: MongoClient = None
_db: Database = None


def init_db(mongo_uri: str, db_name: str = "niknak_chat"):
    """初始化数据库连接"""
    global _client, _db
    _client = MongoClient(mongo_uri)
    _db = _client[db_name]
    return _db


def get_db() -> Database:
    """获取数据库实例"""
    if _db is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")
    return _db

