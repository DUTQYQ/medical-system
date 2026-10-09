import time
import uuid
import bcrypt
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .errors import APIError
from app.models import User, SysConfig

bearer = HTTPBearer(auto_error=False)


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def epoch(db, user_id):
    config = db.scalar(select(SysConfig).where(SysConfig.config_key == f'auth_epoch:{user_id}'))
    return config.config_value if config else '0'


def issue_token(db, user):
    timestamp = int(time.time())
    return jwt.encode({'sub': str(user.id), 'jti': uuid.uuid4().hex, 'iat': timestamp,
                       'exp': timestamp + settings.jwt_expire_seconds, 'epoch': epoch(db, user.id)},
                      settings.jwt_secret, algorithm='HS256')


def get_current_user(request: Request, credentials=Depends(bearer), db: Session = Depends(get_db)):
    if not credentials:
        raise APIError(1001, '未登录或会话已过期', 401)
    try:
        claims = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=['HS256'],
                            options={'require': ['sub', 'exp', 'jti', 'epoch']})
        user_id = int(claims['sub'])
        if len(claims['jti']) != 32:
            raise ValueError('invalid jti')
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise APIError(1001, '会话已过期，请重新登录', 401)
    user = db.get(User, user_id)
    if not user:
        raise APIError(1001, '会话已过期，请重新登录', 401)
    if not user.status:
        raise APIError(1003, '账号已被禁用', 401)
    revoked = db.scalar(select(SysConfig.id).where(SysConfig.config_key == 'jwt_revoked:' + claims['jti']))
    if revoked or claims['epoch'] != epoch(db, user_id):
        raise APIError(1001, '会话已过期，请重新登录', 401)
    request.state.token_claims = claims
    return user


def set_config(db, key, value, group='security'):
    config = db.scalar(select(SysConfig).where(SysConfig.config_key == key).with_for_update())
    if config:
        config.config_value = str(value)
    else:
        db.add(SysConfig(config_key=key, config_value=str(value), config_type='string', group_name=group, enabled=1))
