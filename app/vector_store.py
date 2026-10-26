from pathlib import Path
from functools import lru_cache
from uuid import uuid4
import hashlib

import chromadb
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "chroma_data"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

client = chromadb.PersistentClient(path=str(DB_PATH))

collection = client.get_or_create_collection(
    name="enterprise_documents",
    configuration={"hnsw": {"space": "cosine"}}
)


@lru_cache(maxsize=1)
def get_embedding_model():
    return SentenceTransformer(MODEL_NAME, device="cpu")


def split_text(text, chunk_size=700, overlap=100):
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Invalid chunk settings")

    text = " ".join(text.split())
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


def store_document(filename, text):
    chunks = split_text(text)

    if not chunks:
        return {
            "document_id": None,
            "chunks_stored": 0
        }

    document_id = str(uuid4())
    model = get_embedding_model()

    embeddings = model.encode(
        chunks,
        convert_to_numpy=True
    ).tolist()

    # Remove previously indexed copies of this filename.
    old = collection.get(
        where={"filename": filename}
    )

    if old["ids"]:
        collection.delete(ids=old["ids"])

    ids = [
        f"{document_id}_{i}"
        for i in range(len(chunks))
    ]

    metadatas = [
        {
            "filename": filename,
            "document_id": document_id,
            "chunk_index": i
        }
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return {
        "document_id": document_id,
        "chunks_stored": len(chunks)
    }


def get_document_text():
    """Return text of the indexed document if exactly one exists."""
    stored = collection.get(
        include=["documents", "metadatas"]
    )

    filenames = {
        metadata["filename"]
        for metadata in stored["metadatas"]
    }

    if not filenames:
        return None

    if len(filenames) > 1:
        raise ValueError(
            "Multiple PDFs are indexed. Please use a specific "
            "question or keep only one PDF for summarisation."
        )

    filename = next(iter(filenames))

    entries = sorted(
        zip(stored["documents"], stored["metadatas"]),
        key=lambda entry: entry[1].get("chunk_index", 0)
    )

    # Remove overlapping characters between consecutive chunks.
    parts = []
    previous = ""

    for chunk, metadata in entries:
        if parts and chunk == previous:
            continue

        if parts:
            # Chunks from split_text overlap by 100 characters.
            parts.append(chunk[100:])
        else:
            parts.append(chunk)

        previous = chunk

    return {
        "filename": filename,
        "text": "".join(parts)
    }


def search_documents(query, top_k=5):
    if collection.count() == 0:
        return []

    model = get_embedding_model()

    embedding = model.encode(
        [query],
        convert_to_numpy=True
    ).tolist()

    results = collection.query(
        query_embeddings=embedding,
        n_results=min(max(top_k * 4, 10), collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    matches = []
    seen = set()

    for text, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        content_hash = hashlib.sha256(
            text.strip().encode("utf-8")
        ).hexdigest()

        if content_hash in seen:
            continue

        seen.add(content_hash)

        matches.append({
            "text": text,
            "filename": metadata["filename"],
            "similarity": round(
                max(0, min(1, 1 - distance)),
                4
            )
        })

        if len(matches) >= top_k:
            break

    return matches