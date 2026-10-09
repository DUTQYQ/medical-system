import hashlib
import json
import time
import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.core.database import get_db, now
from app.core.errors import APIError, ok
from app.core.config import settings
from app.core.security import get_current_user, hash_password, verify_password, issue_token, set_config
from app.models import User, SysConfig
from app.services.serializers import user_data
from app.services.thresholds import config_value
from .schemas import Credentials, Register, MeInput, PasswordInput, ConsentInput

router = APIRouter(prefix='/auth', tags=['认证'])


@router.post('/register')
def register(body: Register, db: Session = Depends(get_db)):
    if body.role not in ('ELDER', 'FAMILY'):
        raise APIError(4003, '该角色不允许自助注册，护工与管理员账号由管理员创建')
    if db.scalar(select(User.id).where(User.phone == body.phone)):
        raise APIError(2001, '手机号已注册', 409)
    user = User(phone=body.phone, password_hash=hash_password(body.password), name=body.name, role=body.role)
    db.add(user)
    db.commit()
    return ok(user_data(user))


@router.post('/login')
def login(body: Credentials, db: Session = Depends(get_db)):
    timestamp = int(time.time())
    key = 'login_fail:' + hashlib.sha256(body.phone.encode()).hexdigest()[:32]
    counter = db.scalar(select(SysConfig).where(SysConfig.config_key == key).with_for_update())
    attempt = json.loads(counter.config_value) if counter else {'count': 0, 'until': 0}
    if attempt['until'] <= timestamp:
        attempt = {'count': 0, 'until': timestamp + int(config_value(db, 'login_lock_seconds', '900'))}
    limit = int(config_value(db, 'login_max_attempts', '5'))
    if attempt['count'] >= limit:
        raise APIError(1001, '登录失败次数过多，请稍后重试', 429)
    user = db.scalar(select(User).where(User.phone == body.phone).with_for_update())
    if not user or not verify_password(body.password, user.password_hash):
        attempt['count'] += 1
        set_config(db, key, json.dumps(attempt))
        db.commit()
        raise APIError(1001, '手机号或密码错误', 401)
    if not user.status:
        raise APIError(1003, '账号已被禁用', 401)
    if counter:
        db.delete(counter)
    # Remove expired revocation records without exposing them through config APIs.
    expired = list(db.scalars(select(SysConfig).where(SysConfig.group_name == 'jwt_revocation')))
    for item in expired:
        if int(item.config_value) <= timestamp:
            db.delete(item)
    user.last_login_time = now()
    token = issue_token(db, user)
    db.commit()
    return ok({'token': token, 'expires_in': settings.jwt_expire_seconds, 'user': user_data(user)})


@router.post('/logout')
def logout(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    claims = request.state.token_claims
    set_config(db, 'jwt_revoked:' + claims['jti'], claims['exp'], 'jwt_revocation')
    db.commit()
    return ok()


@router.get('/me')
def me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    result = user_data(user)
    consent = config_value(db, f'privacy_consent:{user.id}')
    result['privacy_consent'] = json.loads(consent) if consent else None
    return ok(result)


@router.put('/me')
def update_me(body: MeInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if body.avatar and not body.avatar.startswith(('https://', 'http://', '/')):
        raise APIError(2001, '头像须为 HTTP 地址或本站路径')
    if body.phone is not None:
        if db.scalar(select(User.id).where(User.phone == body.phone, User.id != user.id)):
            raise APIError(2001, '手机号已被其他用户使用', 409)
        user.phone = body.phone
    user.name = body.name
    if body.avatar is not None:
        user.avatar = body.avatar
    db.commit()
    return ok(user_data(user))


@router.put('/password')
def password(body: PasswordInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.password_hash):
        raise APIError(2001, '原密码错误')
    if len(body.new_password.encode()) > 72:
        raise APIError(2001, '新密码 UTF-8 字节长度不能超过 72')
    user.password_hash = hash_password(body.new_password)
    set_config(db, f'auth_epoch:{user.id}', uuid.uuid4().hex)
    db.commit()
    return ok(message='密码已更新，请重新登录')


@router.post('/privacy-consent')
def consent(body: ConsentInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.accepted:
        raise APIError(2001, '需同意健康档案数据处理授权后继续')
    value = {'accepted': True, 'version': body.version, 'accepted_at': now().strftime('%Y-%m-%d %H:%M:%S')}
    set_config(db, f'privacy_consent:{user.id}', json.dumps(value), 'privacy')
    db.commit()
    return ok(value)
