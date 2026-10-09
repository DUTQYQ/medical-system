"""Preview or add the reviewed official corpus to existing knowledge tables.

Default execution is read-only. --apply adds missing entries and rebuilds the
index. It never creates tables, runs SQL files, or overwrites existing entries.
"""
import argparse
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from sqlalchemy import select
from app.models import KnowledgeDocument

CORPUS_PATH = Path(__file__).resolve().parents[1] / 'data' / 'knowledge_seed.json'
CATEGORIES = {'高血压', '糖尿病', '心率异常', '睡眠', '老年运动', '老年饮食', '常见问题'}
OFFICIAL_HOSTS = {'www.who.int', 'www.nhs.uk'}


def load_corpus(path=CORPUS_PATH):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('schema_version') != 1:
        raise ValueError('不支持的知识语料版本')
    disclaimer = payload.get('disclaimer', '')
    if '健康建议不构成医疗诊断' not in disclaimer:
        raise ValueError('语料缺少健康教育免责声明')
    documents = payload.get('documents', [])
    identifiers, titles = set(), set()
    for entry in documents:
        for key in ('seed_id', 'title', 'category', 'content'):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError(f'知识条目缺少 {key}')
        if len(entry['title']) > 100 or len(entry['content']) > 1000:
            raise ValueError('预置知识正文或标题过长')
        if entry['category'] not in CATEGORIES:
            raise ValueError('知识分类不在已确认的七类中')
        if entry['seed_id'] in identifiers or entry['title'] in titles:
            raise ValueError('预置知识标识或标题重复')
        identifiers.add(entry['seed_id'])
        titles.add(entry['title'])
        if not entry.get('sources'):
            raise ValueError('知识条目必须有官方原始来源')
        for source in entry['sources']:
            url = urlparse(source.get('url', ''))
            if url.scheme != 'https' or url.hostname not in OFFICIAL_HOSTS or url.username or url.password:
                raise ValueError('来源必须是已核对官方机构的 HTTPS 页面')
            if not source.get('title') or not source.get('publisher'):
                raise ValueError('来源标题和发布机构不能为空')
            date.fromisoformat(source['accessed_at'])
            if source.get('published_or_reviewed_at'):
                date.fromisoformat(source['published_or_reviewed_at'])
    if {entry['category'] for entry in documents} != CATEGORIES:
        raise ValueError('语料应覆盖全部七类预置知识')
    return payload


def render_content(entry, disclaimer):
    """Keep attribution in the existing content field; no schema change needed."""
    lines = [entry['content'].strip(), '', disclaimer]
    for source in entry['sources']:
        lines.append(f"官方来源：{source['publisher']}《{source['title']}》 {source['url']}")
        lines.append(f"检索日期：{source['accessed_at']}；来源发布或审阅日期：{source.get('published_or_reviewed_at', '未标注')}")
    lines.append(f"预置资料标识：{entry['seed_id']}")
    return '\n'.join(lines)


def import_knowledge(db, *, reindex=True, dry_run=False, path=CORPUS_PATH):
    """Add only; caller owns commit/rollback. Existing disabled entries stay so."""
    payload = load_corpus(path)
    existing = list(db.scalars(select(KnowledgeDocument)))
    created, skipped = [], []
    for entry in payload['documents']:
        marker = f"预置资料标识：{entry['seed_id']}"
        if any(document.title == entry['title'] or marker in (document.content or '') for document in existing):
            skipped.append(entry['title'])
            continue
        created.append(entry['title'])
        if not dry_run:
            document = KnowledgeDocument(title=entry['title'], category=entry['category'],
                                         content=render_content(entry, payload['disclaimer']), enabled=1)
            db.add(document)
            existing.append(document)
    result = {'dry_run': dry_run, 'added': len(created), 'preserved': len(skipped), 'titles': created,
              'categories': sorted(CATEGORIES)}
    if not dry_run:
        db.flush()
        if reindex:
            from app.agent.rag import rebuild_index
            result['index'] = rebuild_index(db)
    return result


def main():
    parser = argparse.ArgumentParser(description='预览官方知识库增量；--apply 显式追加并重建索引，不覆盖现有内容。')
    parser.add_argument('--apply', action='store_true', help='向当前 DATABASE_URL 已有表追加缺少的条目')
    arguments = parser.parse_args()
    from app.core.database import SessionLocal
    with SessionLocal() as db:
        try:
            result = import_knowledge(db, reindex=arguments.apply, dry_run=not arguments.apply)
            if arguments.apply:
                db.commit()
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception:
            db.rollback()
            raise


if __name__ == '__main__':
    main()
