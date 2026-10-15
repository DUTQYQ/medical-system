"""Explicit additive v2 migration. Default previews; --apply backs up first.

Only additive extension tables are created. Original table definitions and rows
are never altered, deleted or reset. Backup files use existing ignored paths.
"""
import argparse
import gzip
import json
import re
import uuid
from pathlib import Path
from sqlalchemy import inspect, select, func, UniqueConstraint
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import mysql
from app.core.database import Base, engine, SessionLocal, now
import app.models

EXTENSION_NAMES = {
    'profile_threshold_version', 'health_assessment',
    'health_record_void',
    'consultation_intake', 'profile_fact', 'profile_fact_revision', 'advice_card',
    'care_service_catalog', 'care_service_request', 'care_service_event',
    'care_activity', 'care_activity_registration', 'care_equipment',
    'care_equipment_loan', 'care_service_notification',
}
CORE_NAMES = set(Base.metadata.tables) - EXTENSION_NAMES


def comparable_type(value):
    # MySQL reflection adds the database's inherited COLLATE even where the
    # ORM does not prescribe one. Compare storage type/length independently.
    return re.sub(r'\s+COLLATE\s+\w+', '', str(value.compile(dialect=engine.dialect)).upper())


def extension_tables():
    return [table for table in Base.metadata.sorted_tables if table.name in EXTENSION_NAMES]


def schema_preview():
    inspector = inspect(engine)
    missing_core = sorted(name for name in CORE_NAMES if not inspector.has_table(name))
    if missing_core:
        raise RuntimeError('Existing v1 schema is required; refused to initialise a production database')
    incompatible = []
    for table in extension_tables():
        if inspector.has_table(table.name):
            actual = {column['name']: column for column in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in actual:
                    incompatible.append(table.name + '.' + column.name)
                elif comparable_type(column.type) != comparable_type(actual[column.name]['type']):
                    incompatible.append(table.name + '.' + column.name + ':type')
            required_unique = {tuple(c.name for c in constraint.columns) for constraint in table.constraints if isinstance(constraint, UniqueConstraint)}
            actual_unique = {tuple(item['column_names']) for item in inspector.get_unique_constraints(table.name)}
            actual_unique.update(tuple(item['column_names']) for item in inspector.get_indexes(table.name) if item.get('unique'))
            if not required_unique.issubset(actual_unique):
                incompatible.append(table.name + ':unique')
            required_fk = {(tuple(c.name for c in fk.columns), tuple(e.column.name for e in fk.elements), fk.referred_table.name,
                            (fk.ondelete or '').upper()) for fk in table.foreign_key_constraints}
            actual_fk = {(tuple(item['constrained_columns']), tuple(item['referred_columns']), item['referred_table'],
                          (item.get('options', {}).get('ondelete') or '').upper()) for item in inspector.get_foreign_keys(table.name)}
            if not required_fk.issubset(actual_fk):
                incompatible.append(table.name + ':foreign-key')
            if tuple(c.name for c in table.primary_key.columns) != tuple(inspector.get_pk_constraint(table.name)['constrained_columns']):
                incompatible.append(table.name + ':primary-key')
    if incompatible:
        raise RuntimeError('Existing extension schema differs; migration refuses implicit ALTER')
    return sorted(name for name in EXTENSION_NAMES if not inspector.has_table(name))


def backup_original():
    directory = Path(__file__).resolve().parents[1] / 'config.local.migration-backup'
    directory.mkdir(exist_ok=True)
    path = directory / ('v1-' + now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8] + '.json.gz')
    payload = {'created_at': now().isoformat(), 'schema': 'v1-before-additive-v2', 'tables': {}}
    with engine.connect() as connection:
        for name in sorted(CORE_NAMES):
            table = Base.metadata.tables[name]
            payload['tables'][name] = [dict(row) for row in connection.execute(select(table)).mappings()]
    with gzip.open(path, 'wt', encoding='utf-8') as output:
        json.dump(payload, output, ensure_ascii=False, default=str)
    return path, {name: len(rows) for name, rows in payload['tables'].items()}


def apply():
    missing = schema_preview()
    backup, counts = backup_original()
    Base.metadata.create_all(engine, tables=extension_tables(), checkfirst=True)
    with engine.connect() as connection:
        current = {name: connection.scalar(select(func.count()).select_from(Base.metadata.tables[name])) for name in sorted(CORE_NAMES)}
    if counts != current:
        raise RuntimeError('Original rows changed concurrently; inspect backup before proceeding')
    from scripts.seed_services import seed_services
    with SessionLocal() as db:
        seed_services(db, demo=False)
        db.commit()
    result = {'migration': 'v2', 'created_tables': missing, 'extension_table_count': len(EXTENSION_NAMES),
              'original_table_counts_preserved_before_additive_catalog_seed': counts,
              'backup': str(backup), 'completed_at': now().isoformat()}
    manifest = backup.with_suffix('.manifest.json')
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def export_sql(path):
    # Static reviewable SQL, generated from the same metadata as Python.
    dialect = mysql.dialect()
    pieces = ['-- v2 additive extension. Existing v1 tables must already exist.',
              '-- No DROP, ALTER, data reset or production demo inventory.', 'SET NAMES utf8mb4;']
    for table in extension_tables():
        table_sql = str(CreateTable(table, if_not_exists=True).compile(dialect=dialect)).strip()
        pieces.append(table_sql + ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;')
        for index in sorted(table.indexes, key=lambda item: item.name):
            pieces.append(str(CreateIndex(index).compile(dialect=dialect)) + ';')
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('\n\n'.join(pieces) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--export-sql', type=Path)
    args = parser.parse_args()
    if args.export_sql:
        export_sql(args.export_sql)
        print('Reviewable additive SQL exported.')
    if args.apply:
        print(json.dumps(apply(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps({'mode': 'PREVIEW', 'missing_extension_tables': schema_preview(),
                          'original_tables': len(CORE_NAMES), 'extension_tables': len(EXTENSION_NAMES)}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # DB driver messages can contain connection credentials or SQL data.
        print('Migration failed safely: ' + type(exc).__name__)
        raise SystemExit(1)
