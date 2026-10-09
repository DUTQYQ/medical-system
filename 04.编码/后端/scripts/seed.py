"""Explicit, additive demo initialization for isolated SQLite only.

Usage: DATABASE_URL=sqlite:///... python -m scripts.seed --demo
Never run schema.sql/init_data.sql against an existing deployment.
"""
import argparse
import json
from datetime import date
from sqlalchemy import select
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.core.errors import APIError
from app.models import User, ElderProfile, FamilyBind, CareRelation, SysConfig, KnowledgeDocument

THRESHOLDS = {
    'BLOOD_PRESSURE_SYSTOLIC': {'level0': '90~139', 'level1': '140~159', 'level2': '160~179', 'level3': '<90 或 >=180'},
    'BLOOD_PRESSURE_DIASTOLIC': {'level0': '60~89', 'level1': '90~99', 'level2': '100~109', 'level3': '<60 或 >=110'},
    'BLOOD_SUGAR': {'level0': '3.9~6.1', 'level1': '6.2~7.0', 'level2': '7.1~11.1', 'level3': '<3.9 或 >=11.2'},
    'HEART_RATE': {'level0': '60~100', 'level1': '50~59,101~110', 'level2': '40~49,111~130', 'level3': '<40 或 >130'},
    'SLEEP_HOURS': {'level0': '>=7', 'level1': '6~7', 'level2': '5~6', 'level3': '<5'},
    'STEP_COUNT': {'level0': '>=6000', 'level1': '4000~5999', 'level2': '2000~3999', 'level3': '<2000'},
}
SYSTEM_CONFIG = {
    'family_bind_max': '5', 'alert_unread_poll_sec': '30', 'ai_summary_timeout_sec': '8',
    'ai_summary_retry': '1', 'ai_daily_limit': '50', 'ai_question_max_chars': '2000',
    'login_max_attempts': '5', 'login_lock_seconds': '900',
    'emergency_keywords': json.dumps(['胸痛', '胸口很痛', '胸口疼', '呼吸困难', '喘不上气', '意识丧失', '昏厥', '无法起身', '大量出血', '言语不清'], ensure_ascii=False),
}


def seed_database(db, demo=False):
    for key, value in THRESHOLDS.items():
        if not db.scalar(select(SysConfig.id).where(SysConfig.config_key == key)):
            db.add(SysConfig(config_key=key, config_value=json.dumps(value, ensure_ascii=False), config_type='threshold', group_name='threshold', description='演示参考阈值，健康建议不构成医疗诊断', enabled=1))
    for key, value in SYSTEM_CONFIG.items():
        if not db.scalar(select(SysConfig.id).where(SysConfig.config_key == key)):
            db.add(SysConfig(config_key=key, config_value=value, config_type='json' if key == 'emergency_keywords' else 'number', group_name='system', enabled=1))
    db.flush()
    if demo:
        accounts = {}
        password_hash = hash_password('Abc123456')
        for index, role, name in [(1, 'ADMIN', '系统管理员'), (2, 'ELDER', '张桂兰'), (3, 'FAMILY', '李强'), (4, 'CARE', '王护工')]:
            phone = f'1300000000{index}'
            user = db.scalar(select(User).where(User.phone == phone))
            if not user:
                user = User(phone=phone, password_hash=password_hash, role=role, name=name, status=1)
                db.add(user)
                db.flush()
            accounts[role] = user
        profile = db.scalar(select(ElderProfile).where(ElderProfile.user_id == accounts['ELDER'].id, ElderProfile.deleted == 0))
        if not profile:
            profile = ElderProfile(user_id=accounts['ELDER'].id, name='张桂兰', gender='F', birthday=date(1948, 3, 12),
                                   height=158, weight=62, chronic_tags='["高血压"]', emergency_contact='李强', emergency_phone=accounts['FAMILY'].phone)
            db.add(profile)
            db.flush()
        if not db.scalar(select(FamilyBind.id).where(FamilyBind.profile_id == profile.id, FamilyBind.family_user_id == accounts['FAMILY'].id)):
            db.add(FamilyBind(profile_id=profile.id, family_user_id=accounts['FAMILY'].id, relation='儿子', status='APPROVED', approved_by=accounts['ELDER'].id))
        if not db.scalar(select(CareRelation.id).where(CareRelation.profile_id == profile.id, CareRelation.care_user_id == accounts['CARE'].id)):
            db.add(CareRelation(profile_id=profile.id, care_user_id=accounts['CARE'].id, status=1))
        from scripts.import_knowledge import import_knowledge
        try:
            with db.begin_nested():
                import_knowledge(db, reindex=True)
        except APIError as exc:
            if exc.code != 3001:
                raise
            # Optional semantic embedding configuration must not prevent the
            # health/alert demo from starting. Preserve canonical documents,
            # explicitly report that their vector index is unavailable.
            import_knowledge(db, reindex=False)
            print('官方知识条目已追加；向量索引未就绪，AI 检索将明确报告不可用。')
    db.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true', required=True)
    parser.parse_args()
    if engine.dialect.name != 'sqlite':
        raise SystemExit('拒绝初始化非 SQLite 数据库；现有 MySQL 只允许使用已有表与数据')
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_database(db, demo=True)
    print('独立 SQLite 演示库已完成幂等追加初始化。账号 13000000001~04，密码 Abc123456。未创建健康指标或预警记录。')


if __name__ == '__main__':
    main()
