"""Public runtime identity for pairing launchers with the intended service."""
import hashlib
from pathlib import Path


def source_revision():
    root = Path(__file__).resolve().parents[1]
    entries = [path.relative_to(root).as_posix() + ':' + hashlib.sha256(path.read_bytes()).hexdigest()
               for path in sorted(root.rglob('*.py'))]
    return hashlib.sha256('\n'.join(entries).encode('utf-8')).hexdigest()


RUNTIME_REVISION = source_revision()
