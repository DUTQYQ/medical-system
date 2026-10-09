"""Verify configured MySQL read-only; optionally test a new disposable database."""
import argparse
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import URL, create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / '04.编码' / '后端'
sys.path.insert(0, str(BACKEND))


def configured_url():
    values = dotenv_values(BACKEND / '.env')
    if values.get('DATABASE_URL'):
        from sqlalchemy.engine import make_url
        result = make_url(values['DATABASE_URL'])
        if not result.drivername.startswith('mysql'):
            raise ValueError('The configured database is not MySQL')
        return result
    return URL.create('mysql+pymysql', username=values.get('DB_USER', 'root'),
                      password=values.get('DB_PASSWORD', ''),
                      host=values.get('DB_HOST', '127.0.0.1'), port=int(values.get('DB_PORT', '3306')),
                      database=values.get('DB_NAME', 'kangyang'), query={'charset': 'utf8mb4'})


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--run-tests', action='store_true')
    parsed = args.parse_args()
    url = configured_url()
    engine = create_engine(url, pool_pre_ping=True)
    from app.models import Base
    with engine.connect() as conn:
        version = conn.scalar(text('SELECT VERSION()'))
        print('MySQL connection: OK; version=' + str(version))
    actual = inspect(engine)
    missing = []
    for table in Base.metadata.sorted_tables:
        if not actual.has_table(table.name):
            missing.append(table.name)
            continue
        actual_columns = {item['name'] for item in actual.get_columns(table.name)}
        missing.extend(table.name + '.' + column.name for column in table.columns if column.name not in actual_columns)
    print('Existing database schema: ' + ('MATCH (15 tables; no data modified)' if not missing else 'MISSING ' + ', '.join(missing)))
    engine.dispose()
    if not parsed.run_tests:
        return 0 if not missing else 1
    test_name = 'kangyang_codex_test_' + uuid.uuid4().hex[:8]
    if not re.fullmatch(r'kangyang_codex_test_[0-9a-f]{8}', test_name) or test_name == url.database:
        raise ValueError('Unsafe temporary database name')
    admin_engine = create_engine(url.set(database=None), pool_pre_ping=True)
    created = False
    try:
        with admin_engine.begin() as conn:
            conn.execute(text('CREATE DATABASE `' + test_name + '` CHARACTER SET utf8mb4'))
            created = True
        child_env = os.environ.copy()
        child_env['KANGYANG_TEST_DATABASE_URL'] = url.set(database=test_name).render_as_string(hide_password=False)
        child_env['KANGYANG_TEMP_DB_NAME'] = test_name
        print('Running acceptance tests on a new disposable MySQL database')
        return subprocess.run([sys.executable, '-m', 'pytest', str(ROOT / '05.集成测试'), '-q'],
                              cwd=str(BACKEND), env=child_env).returncode
    finally:
        if created:
            with admin_engine.begin() as conn:
                conn.execute(text('DROP DATABASE `' + test_name + '`'))
            print('Disposable MySQL database removed; original database untouched')
        admin_engine.dispose()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        # Connection errors are sanitized to avoid exposing environment values.
        print('MySQL verification failed: ' + type(error).__name__)
        original = getattr(error, 'orig', None)
        if original and original.args and isinstance(original.args[0], int):
            print('Database error code: ' + str(original.args[0]))
        raise SystemExit(1)
