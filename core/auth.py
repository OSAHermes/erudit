"""
认证模块
"""
import secrets
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import validate_token, get_db

auth_scheme = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """获取当前认证用户"""
    token = validate_token(credentials.credentials)
    if not token:
        raise HTTPException(status_code=401, detail="未授权或 Token 已过期")
    return token