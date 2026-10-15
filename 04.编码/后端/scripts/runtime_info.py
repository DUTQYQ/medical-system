"""Print only the source revision; no environment or credentials are exposed."""
from app.core.runtime import source_revision

if __name__ == '__main__':
    print(source_revision())
