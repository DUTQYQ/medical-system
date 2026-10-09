"""Generate a missing local JWT secret without printing or replacing secrets."""
import secrets
from pathlib import Path
from dotenv import dotenv_values, set_key


def main():
    path = Path(__file__).resolve().parents[1] / '.env'
    if not path.is_file():
        raise SystemExit('请先将 .env.example 复制为 .env 并填写 MySQL 配置')
    values = dotenv_values(path)
    if not (values.get('SECRET_KEY') or values.get('JWT_SECRET')):
        set_key(str(path), 'SECRET_KEY', secrets.token_hex(32))
        print('已为本机 .env 生成持久 JWT 密钥；未输出密钥。')
    else:
        print('本机 JWT 密钥已存在，保留原值。')


if __name__ == '__main__':
    main()
