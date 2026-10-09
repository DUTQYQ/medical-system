from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import install_handlers, ok
from app.core.database import get_db
from app.api import auth, profiles, health, alerts, family, care, admin, ai
from app.services.recovery import recovery_enabled, recover_once


@asynccontextmanager
async def lifespan(app):
    if not settings.database_url:
        raise RuntimeError('请配置 DATABASE_URL 或 DB_HOST/DB_USER/DB_PASSWORD/DB_NAME；服务不会自动创建或重建 MySQL')
    if len(settings.jwt_secret) < 32:
        raise RuntimeError('JWT_SECRET/SECRET_KEY 至少需要 32 个字符')
    sweep = None
    if recovery_enabled():
        await asyncio.to_thread(recover_once)
        async def sweep_interrupted_summaries():
            # An immediate restart may be inside the timeout margin; re-check
            # later so those abandoned PENDING rows do not remain stuck forever.
            while True:
                await asyncio.sleep(30)
                await asyncio.to_thread(recover_once)
        sweep = asyncio.create_task(sweep_interrupted_summaries())
    try:
        yield
    finally:
        if sweep:
            sweep.cancel()
            await asyncio.gather(sweep, return_exceptions=True)


app = FastAPI(title='基于 AI 智能体的康养系统', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], allow_headers=['Authorization', 'Content-Type'])
install_handlers(app)
for router in (auth.router, profiles.router, health.router, alerts.router, alerts.notifications, family.router,
               care.router, admin.router, admin.config_router, ai.router):
    app.include_router(router, prefix='/api')


@app.get('/api/healthz', tags=['服务状态'])
def healthz(db: Session = Depends(get_db)):
    db.execute(select(1)).scalar_one()
    return ok({'service': 'kangyang', 'version': '1.0.0', 'database': 'available', 'disclaimer': '健康建议不构成医疗诊断'})
