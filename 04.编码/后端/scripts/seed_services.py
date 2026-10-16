"""院内服务增量默认项，现有库只加目录；不虚构机构库存。"""
from datetime import timedelta
import json
from sqlalchemy import select
from app.core.database import now
from app.models import User, SysConfig, ActivityTemplate
from app.models.care_services import ServiceCatalog, Activity, Equipment
from app.services.care_services import DEFAULT_CATALOG


def seed_services(db, demo=False):
    """Caller owns the transaction; preserve existing edits and disabled items."""
    added = 0
    for key, value, description in [
        ('FLUCTUATION_THRESHOLD', '0.2', '个人前七天有效历史样本的波动提醒比例，不代表医疗诊断或自动预警'),
        ('ai_summary_daily_limit', '100', '全院每日可选 AI 摘要请求上限，不限制预警生成'),
        ('ai_summary_warning_daily_limit', '3', '单条预警每日摘要请求上限'),
        ('ai_summary_cooldown_seconds', '60', '同一预警摘要请求冷却秒数')]:
        if not db.scalar(select(SysConfig.id).where(SysConfig.config_key == key)):
            db.add(SysConfig(config_key=key, config_value=value, config_type='number',
                group_name='system', description=description, enabled=1))
    for item in DEFAULT_CATALOG:
        if not db.scalar(select(ServiceCatalog.id).where(ServiceCatalog.category == item['category'])):
            db.add(ServiceCatalog(**item, enabled=1))
            added += 1
    if not db.scalar(select(SysConfig.id).where(SysConfig.config_key == 'service_call_timeout_seconds')):
        db.add(SysConfig(config_key='service_call_timeout_seconds', config_value='300', config_type='number',
                         group_name='services', description='院内呼叫无人应答升级管理员的秒数', enabled=1))
    if not db.scalar(select(SysConfig.id).where(SysConfig.config_key == 'care_health_data_fresh_hours')):
        db.add(SysConfig(config_key='care_health_data_fresh_hours', config_value='72', config_type='number',
                         group_name='services', description='护工工作台健康数据待更新的小时数，仅表示记录新鲜度', enabled=1))
    if demo:
        # Fictional suggestions only in the isolated demo database. The real
        # institution must create and confirm its own catalogue and rules.
        for code, name, category, intensity in [
            ('SUNBATH', '日光浴', '户外', 'LOW'), ('TAICHI', '太极拳', '养生', 'MODERATE'),
            ('WALK', '散步', '有氧', 'MODERATE'), ('FINGER', '手指操', '康复', 'LOW'),
            ('BREATH', '呼吸训练', '康复', 'LOW'), ('STRETCH', '关节拉伸', '康复', 'LOW')]:
            if not db.scalar(select(ActivityTemplate.id).where(ActivityTemplate.code == code)):
                db.add(ActivityTemplate(code=code, name='演示：'+name, category=category, intensity=intensity,
                    description='演示活动类型；实际参与、时长、强度及陪同要求由工作人员核验。',
                    benefits='用于沟通个人兴趣与活动安排，不承诺治疗或健康效果。', duration_hint='由工作人员根据实际情况安排',
                    rules=json.dumps({'suitable': {'min_age': 60}, 'caution': {'max_risk_level': 2}}, ensure_ascii=False),
                    contraindications='如有不适，先联系现场工作人员。', enabled=1))
        creator = db.scalar(select(User).where(User.role == 'ADMIN', User.status == 1).order_by(User.id))
        if creator:
            for title, category, location, capacity in [
                    ('演示：棋牌交流活动', 'ENTERTAINMENT', '演示活动室', 4),
                    ('演示：午后轻松散步', 'EXERCISE', '演示院内花园', 6)]:
                if not db.scalar(select(Activity.id).where(Activity.title == title)):
                    db.add(Activity(title=title, category=category, location=location, capacity=capacity,
                        reserved_count=0, start_at=now()+timedelta(days=1), end_at=now()+timedelta(days=1, hours=1),
                        description='仅独立演示库样例，实际参加由工作人员确认适宜性。', status='PUBLISHED', creator_id=creator.id))
        for name, total in [('演示轮椅', 3), ('演示助行器', 2)]:
            if not db.scalar(select(Equipment.id).where(Equipment.name == name)):
                db.add(Equipment(name=name, total=total, available=total, damaged=0,
                                 description='仅独立演示库样例，不代表真实库存', enabled=1))
    db.flush()
    return {'catalog_added': added, 'demo': demo}
