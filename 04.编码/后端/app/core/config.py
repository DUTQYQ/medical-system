import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import URL

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / '.env', override=False)


class Settings:
    database_url = os.getenv('DATABASE_URL', '')
    if not database_url and os.getenv('DB_USER') and os.getenv('DB_NAME'):
        database_url = URL.create('mysql+pymysql', username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD', ''),
                                  host=os.getenv('DB_HOST', '127.0.0.1'), port=int(os.getenv('DB_PORT', '3306')),
                                  database=os.getenv('DB_NAME'), query={'charset': 'utf8mb4'}).render_as_string(hide_password=False)
    jwt_secret = os.getenv('JWT_SECRET', os.getenv('SECRET_KEY', ''))
    jwt_expire_seconds = int(os.getenv('JWT_EXPIRE_SECONDS', str(int(os.getenv('JWT_EXPIRE_MINUTES', '1440')) * 60)))
    cors_origins = [v.strip() for v in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if v.strip()]
    llm_provider = os.getenv('LLM_PROVIDER', 'deepseek')


settings = Settings()
