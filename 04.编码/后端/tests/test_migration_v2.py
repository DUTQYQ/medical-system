import pytest
from sqlalchemy import MetaData, UniqueConstraint
from test_business import setup
from scripts import migrate_v2
from app.core.database import Base


def test_migration_preview_accepts_complete_extension_schema(setup, monkeypatch):
    _, sessions = setup
    monkeypatch.setattr(migrate_v2, 'engine', sessions.kw['bind'])
    assert migrate_v2.schema_preview() == []
    assert len(migrate_v2.extension_tables()) == 16


def test_migration_refuses_existing_extension_without_intake_unique_key(setup, monkeypatch):
    _, sessions = setup
    engine = sessions.kw['bind']
    monkeypatch.setattr(migrate_v2, 'engine', engine)
    clone = MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(clone)
    damaged = clone.tables['consultation_intake']
    for constraint in list(damaged.constraints):
        if isinstance(constraint, UniqueConstraint):
            damaged.constraints.remove(constraint)
    Base.metadata.tables['consultation_intake'].drop(engine)
    damaged.create(engine)
    with pytest.raises(RuntimeError):
        migrate_v2.schema_preview()
