import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.llm import ollama


_client = chromadb.PersistentClient(
    path=settings.chroma_path,
    settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
)
_collection = _client.get_or_create_collection(
    name="kb",
    metadata={"hnsw:space": "cosine"},
)


async def add_chunks(doc_id: str, doc_name: str, chunks: list[str]) -> None:
    embeddings = [await ollama.embed(c) for c in chunks]
    ids = [f"{doc_id}::{i}" for i in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "doc_name": doc_name, "chunk_idx": i}
        for i in range(len(chunks))
    ]
    _collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )


async def query(text: str, top_k: int) -> list[dict]:
    vec = await ollama.embed(text)
    res = _collection.query(query_embeddings=[vec], n_results=top_k)
    out: list[dict] = []
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for d, m, dist in zip(docs, metas, dists):
        out.append({"text": d, "metadata": m or {}, "distance": float(dist)})
    return out


def list_documents() -> list[dict]:
    res = _collection.get()
    seen: dict[str, dict] = {}
    for m in res.get("metadatas") or []:
        if not m:
            continue
        did = m.get("doc_id")
        if did and did not in seen:
            seen[did] = {"doc_id": did, "doc_name": m.get("doc_name", "")}
    return sorted(seen.values(), key=lambda x: x["doc_name"])


def delete_document(doc_id: str) -> int:
    res = _collection.get(where={"doc_id": doc_id})
    ids = res.get("ids", [])
    if ids:
        _collection.delete(ids=ids)
    return len(ids)
