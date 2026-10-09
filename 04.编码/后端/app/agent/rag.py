"""Chroma cosine retrieval with offline lexical feature hashing.

The 512-dimensional n-gram embedding is deterministic and does not require a
model download. It is NOT a learned semantic embedding, so paraphrase recall is
limited. Both this limitation and the embedding name are returned explicitly.
"""
import hashlib
import math
import os
import re
import threading
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sqlalchemy import select, delete
from app.models import KnowledgeDocument, KnowledgeChunk
from app.core.errors import APIError

DIMENSIONS = 512
EMBEDDING_NAME = 'hash-ngram-512'
_lock = threading.RLock()
_clients = {}
_signatures = {}
_models = {}


def embedding_info():
    provider = os.getenv('EMBEDDING_PROVIDER', 'hash').strip().lower()
    if provider == 'hash':
        return {'embedding': EMBEDDING_NAME, 'semantic_embedding': False, 'provider': 'hash'}
    if provider not in ('sentence-transformers', 'local'):
        raise APIError(3001, '不支持的向量提供方；请选择 hash 或 sentence-transformers', 503)
    raw_path = os.getenv('EMBEDDING_MODEL_PATH', '').strip()
    path = Path(raw_path).resolve() if raw_path else None
    if path is None or not path.is_dir() or not (path / 'modules.json').is_file():
        raise APIError(3001, '本地语义向量需要已有 SentenceTransformer 模型目录及 modules.json；系统不会下载模型', 503)
    try:
        import sentence_transformers  # noqa: F401; optional dependency, never downloaded here
    except ImportError:
        raise APIError(3001, '尚未安装本地语义向量可选依赖 sentence-transformers；可继续使用 hash', 503)
    return {'embedding': 'sentence-transformers:' + path.name, 'semantic_embedding': True, 'provider': 'sentence-transformers'}


def _local_model():
    from sentence_transformers import SentenceTransformer
    path = Path(os.environ['EMBEDDING_MODEL_PATH']).resolve()
    key = (str(path), (path / 'modules.json').stat().st_mtime_ns)
    if key not in _models:
        try:
            _models[key] = SentenceTransformer(str(path), device='cpu', local_files_only=True, trust_remote_code=False)
        except Exception:
            raise APIError(3001, '本地语义模型无法从已提供文件加载；系统不会联网下载或回退伪装成功', 503)
    return _models[key]


def embed(text):
    info = embedding_info()
    if info['semantic_embedding']:
        try:
            output = _local_model().encode([str(text)], normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True)[0]
            vector = output.tolist() if hasattr(output, 'tolist') else list(output)
            if not vector or not all(math.isfinite(float(value)) for value in vector):
                raise ValueError('invalid embedding')
            return [float(value) for value in vector]
        except APIError:
            raise
        except Exception:
            raise APIError(3001, '本地语义向量生成失败，请检查模型目录与依赖', 503)
    text = re.sub(r'\s+', '', str(text).lower())
    features = [text[i:i + size] for size in (1, 2, 3) for i in range(max(0, len(text) - size + 1))]
    vector = [0.0] * DIMENSIONS
    for token in features:
        index = int.from_bytes(hashlib.blake2b(token.encode('utf-8'), digest_size=4).digest(), 'big') % DIMENSIONS
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    else:
        vector[0] = 1.0
    return vector


def _collection(db):
    backend_root = Path(__file__).resolve().parents[2]
    path = Path(os.getenv('CHROMA_PATH') or os.getenv('VECTOR_STORE_PATH') or 'config.local.chroma')
    directory = str((path if path.is_absolute() else backend_root / path).resolve())
    database_identity = str(db.get_bind().url)
    info = embedding_info()
    embedding_identity = info['embedding']
    if info['semantic_embedding']:
        path = Path(os.environ['EMBEDDING_MODEL_PATH']).resolve()
        embedding_identity += ':' + str(path) + ':' + str((path / 'modules.json').stat().st_mtime_ns)
    # Different embeddings have distinct collections, including different dimensions.
    collection_name = 'knowledge-' + hashlib.sha256((database_identity + '|' + embedding_identity).encode()).hexdigest()[:20]
    if directory not in _clients:
        _clients[directory] = chromadb.PersistentClient(path=directory, settings=Settings(anonymized_telemetry=False))
    collection = _clients[directory].get_or_create_collection(collection_name, metadata={'hnsw:space': 'cosine'}, embedding_function=None)
    return collection, (directory, collection_name)


def _documents(db):
    return list(db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.enabled == 1).order_by(KnowledgeDocument.id)))


def _signature(documents):
    return hashlib.sha256('\n'.join(f'{doc.id}:{doc.title}:{doc.content}' for doc in documents).encode()).hexdigest()


def rebuild_index(db):
    """Rebuild from authorized administrator-managed docs; caller owns commit."""
    with _lock:
        docs = _documents(db)
        collection, key = _collection(db)
        info = embedding_info()
        ids, texts, metadata, vectors = [], [], [], []
        db.execute(delete(KnowledgeChunk))
        for doc in docs:
            content = (doc.content or '').strip()
            for index, start in enumerate(range(0, len(content), 420)):
                text = content[start:start + 500]
                vector = embed(doc.title + '\n' + text)
                ids.append(f'{doc.id}:{index}')
                texts.append(text)
                metadata.append({'doc_id': doc.id, 'title': doc.title, 'embedding': info['embedding']})
                vectors.append(vector)
                db.add(KnowledgeChunk(doc_id=doc.id, chunk_index=index, chunk_text=text, embedding=vector))
        existing = collection.get(include=[])['ids']
        if existing:
            collection.delete(ids=existing)
        for start in range(0, len(ids), 100):
            collection.upsert(ids=ids[start:start + 100], documents=texts[start:start + 100], metadatas=metadata[start:start + 100], embeddings=vectors[start:start + 100])
        db.flush()
        _signatures[key] = _signature(docs)
        return {'documents': len(docs), 'chunks': len(ids), **info}


def retrieve(db, question, top_k=None):
    with _lock:
        if top_k is None:
            try:
                top_k = max(1, min(10, int(os.getenv('RAG_TOP_K', '3'))))
            except ValueError:
                top_k = 3
        docs = _documents(db)
        collection, key = _collection(db)
        if _signatures.get(key) != _signature(docs):
            rebuild_index(db)
        count = collection.count()
        if not count:
            return []
        result = collection.query(query_embeddings=[embed(question)], n_results=min(max(1, top_k), count), include=['documents', 'metadatas', 'distances'])
        info = embedding_info()
        return [{'title': meta['title'], 'text': text, 'score': round(max(0.0, 1.0 - distance), 4), **info}
                for text, meta, distance in zip(result['documents'][0], result['metadatas'][0], result['distances'][0])]
