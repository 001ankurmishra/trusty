"""
FR-08 Enterprise RAG - local embeddings, local vector DB (ChromaDB embedded mode,
so no separate Qdrant server/container needed - lighter for a 16GB laptop),
project + permission filtering, page citations.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from ..core.config import settings

# Disable ChromaDB telemetry — must NOT phone home in air-gapped mode
_client = chromadb.PersistentClient(
    path=settings.CHROMA_DIR,
    settings=ChromaSettings(anonymized_telemetry=False),
)
_collection = _client.get_or_create_collection("sova_docs")
_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(settings.EMBED_MODEL_LOCAL)
    return _embedder


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start < 0:
            break
    return [c for c in chunks if c.strip()]


def ingest_document(doc_id: str, project_id: str, filename: str, pages: list, confidentiality: str = "Internal", doc_role: str = "OTHER", version: str = "1.0"):
    embedder = _get_embedder()
    ids, docs, metas = [], [], []
    for page in pages:
        for j, chunk in enumerate(chunk_text(page["text"])):
            cid = f"{doc_id}_{page['page']}_{j}"
            ids.append(cid)
            docs.append(chunk)
            metas.append({
                "document_id": doc_id,
                "project_id": project_id,
                "filename": filename,
                "page": page["page"],
                "confidentiality": confidentiality,
                "doc_role": doc_role,
                "version": version,
                "low_confidence": page.get("low_confidence", False),
            })
    if not docs:
        return 0
    embeddings = embedder.encode(docs).tolist()
    _collection.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)
    return len(docs)


def search(query: str, project_id: str, top_k: int = 5, user_role: str = "USER"):
    """
    Search for relevant chunks in the project's knowledge base.
    Confidentiality filter: 'Confidential' chunks only returned for ADMIN/REVIEWER.
    """
    embedder = _get_embedder()
    q_emb = embedder.encode([query]).tolist()
    results = _collection.query(
        query_embeddings=q_emb,
        n_results=top_k * 2,  # fetch more so we can filter
        where={"project_id": project_id},  # FR-08 project boundary filtering
        include=["documents", "metadatas", "distances"],
    )
    out = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            # Confidentiality filter
            if meta.get("confidentiality") == "Confidential" and user_role not in ("ADMIN", "REVIEWER"):
                continue
            out.append({
                "chunk": results["documents"][0][i],
                "filename": meta["filename"],
                "page": meta["page"],
                "low_confidence": meta.get("low_confidence", False),
                "confidentiality": meta.get("confidentiality", "Internal"),
                "doc_role": meta.get("doc_role", "OTHER"),
                "version": meta.get("version", "1.0"),
                "distance": results["distances"][0][i] if "distances" in results and results["distances"] else None,
            })
            if len(out) >= top_k:
                break
    return out

def get_project_rules(project_id: str):
    """
    Fetch all SOP chunks for a project to extract active rules.
    """
    results = _collection.get(
        where={
            "$and": [
                {"project_id": project_id},
                {"doc_role": "SOP"}
            ]
        },
        include=["documents", "metadatas"]
    )
    out = []
    if results["ids"]:
        for i in range(len(results["ids"])):
            meta = results["metadatas"][i]
            out.append({
                "chunk": results["documents"][i],
                "filename": meta["filename"],
                "version": meta.get("version", "1.0"),
                "page": meta["page"]
            })
    return out


def delete_document(doc_id: str):
    """
    Delete all chunks associated with a specific document ID.
    """
    _collection.delete(where={"document_id": doc_id})
    # Also attempt to delete vision chunks if they exist
    _collection.delete(where={"document_id": f"{doc_id}_vision"})
