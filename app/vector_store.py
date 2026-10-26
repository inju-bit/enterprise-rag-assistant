from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "chroma_data"

client = chromadb.PersistentClient(path=str(DB_PATH))

collection = client.get_or_create_collection(
    name="enterprise_documents",
    metadata={"hnsw:space": "cosine"}
)


@lru_cache(maxsize=1)
def embedding_model():
    return SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2",
        device="cpu"
    )


def split_text(text, size=700, overlap=100):
    text = " ".join(text.split())

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


def delete_vectors(document_id):
    existing = collection.get(
        where={"document_id": document_id}
    )

    ids = existing.get("ids", [])

    if ids:
        collection.delete(ids=ids)

    return len(ids)


def index_document(document_id, filename, text):
    chunks = split_text(text)

    if not chunks:
        raise ValueError("PDF has no extractable text.")

    # Remove any incomplete index from an earlier attempt.
    delete_vectors(document_id)

    batch_size = 32

    try:
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]

            embeddings = embedding_model().encode(
                batch,
                convert_to_numpy=True
            ).tolist()

            collection.add(
                ids=[str(uuid4()) for _ in batch],
                documents=batch,
                embeddings=embeddings,
                metadatas=[
                    {
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": start + index
                    }
                    for index in range(len(batch))
                ]
            )
    except Exception:
        delete_vectors(document_id)
        raise

    return len(chunks)


def search_documents(query, top_k=5, document_id=None):
    if not document_id:
        return []

    existing = collection.get(
        where={"document_id": document_id}
    )

    count = len(existing.get("ids", []))

    if count == 0:
        return []

    query_embedding = embedding_model().encode(
        [query],
        convert_to_numpy=True
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, count),
        where={"document_id": document_id},
        include=["documents", "metadatas", "distances"]
    )

    matches = []

    for text, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        matches.append({
            "text": text,
            "filename": metadata.get("filename", "Document"),
            "document_id": document_id,
            "similarity": round(
                max(0, min(1, 1 - distance)),
                4
            )
        })

    return matches