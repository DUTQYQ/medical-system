from contextlib import asynccontextmanager
import asyncio
import logging
import os
from fastapi import FastAPI, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import install_handlers, ok
from app.core.database import get_db, SessionLocal
from app.core.runtime import RUNTIME_REVISION
from app.api import auth, profiles, health, alerts, family, care, admin, ai, personal_threshold, intake, services
from app.api import activities
from app.services.recovery import recovery_enabled, recover_once


@asynccontextmanager
async def lifespan(app):
    if not settings.database_url:
        raise RuntimeError('请配置 DATABASE_URL 或 DB_HOST/DB_USER/DB_PASSWORD/DB_NAME；服务不会自动创建或重建 MySQL')
    if len(settings.jwt_secret) < 32:
        raise RuntimeError('JWT_SECRET/SECRET_KEY 至少需要 32 个字符')
    sweep = None
    dispatch = None
    if recovery_enabled():
        await asyncio.to_thread(recover_once)
        async def sweep_interrupted_summaries():
            # An immediate restart may be inside the timeout margin; re-check
            # later so those abandoned PENDING rows do not remain stuck forever.
            while True:
                await asyncio.sleep(30)
                await asyncio.to_thread(recover_once)
        sweep = asyncio.create_task(sweep_interrupted_summaries())
    # Site calls are deterministic and independent of model availability. Test
    # clients that override get_db must never spawn a worker on the real DB.
    if get_db not in app.dependency_overrides and os.getenv('SERVICE_DISPATCH_ENABLED', 'true').lower() == 'true':
        def escalate_calls():
            from app.services.care_services import escalate_overdue_calls
            with SessionLocal() as db:
                escalate_overdue_calls(db)
                db.commit()
        async def dispatch_calls():
            while True:
                await asyncio.sleep(15)
                try:
                    await asyncio.to_thread(escalate_calls)
                except Exception as exc:
                    logging.getLogger(__name__).warning('Service dispatch retry: %s', type(exc).__name__)
        dispatch = asyncio.create_task(dispatch_calls())
    try:
        yield
    finally:
        tasks = [task for task in (sweep, dispatch) if task]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title='基于 AI 智能体的康养系统', version='2.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], allow_headers=['Authorization', 'Content-Type'])
install_handlers(app)
for router in (auth.router, profiles.router, health.router, alerts.router, alerts.notifications, family.router,
               care.router, admin.router, admin.config_router, ai.router, personal_threshold.router, intake.router, services.router, activities.router):
    app.include_router(router, prefix='/api')


@app.get('/api/healthz', tags=['服务状态'])
def healthz(db: Session = Depends(get_db)):
    db.execute(select(1)).scalar_one()
    dialect = db.get_bind().dialect.name
    demo = os.getenv('DEMO_MODE', '').lower() in ('true', '1', 'yes') and dialect == 'sqlite'
    return ok({'service': 'kangyang', 'version': '2.0.0', 'database': 'available',
        'database_mode': 'DEMO_SQLITE' if demo else dialect.upper(),
        'runtime_revision': RUNTIME_REVISION, 'process_id': os.getpid(),
        'disclaimer': '健康建议不构成医疗诊断'})
