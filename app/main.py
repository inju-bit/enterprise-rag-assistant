import logging
import threading
from pathlib import Path
from uuid import uuid4

from fastapi import (
    FastAPI, UploadFile, File, HTTPException, BackgroundTasks
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.pdf_processor import extract_text_from_pdf
from app.document_store import (
    init_documents,
    create_document,
    get_document,
    list_documents,
    update_document,
    remove_document,
    UPLOAD_DIR
)
from app.vector_store import (
    index_document,
    delete_vectors,
    search_documents
)
from app.rag import generate_answer

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enterprise AI Knowledge Assistant",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"]
)

MAX_UPLOAD = 10 * 1024 * 1024

# Protect indexing and deletion against concurrent modifications.
index_lock = threading.RLock()

init_documents()


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: str
    top_k: int = Field(default=5, ge=1, le=20)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    document_id: str
    top_k: int = Field(default=5, ge=1, le=20)


def public_document(document):
    return {
        "id": document["id"],
        "filename": document["filename"],
        "status": document["status"],
        "pages": document["pages"],
        "chunks": document["chunks"],
        "error": document["error"],
        "created_at": document["created_at"]
    }


def process_document(document_id):
    # Serial execution prevents expensive embedding jobs
    # from competing for the Intel Mac's CPU.
    with index_lock:
        document = get_document(document_id)

        if not document:
            return

        try:
            update_document(
                document_id,
                status="indexing",
                error=None
            )

            path = Path(document["stored_path"])
            content = path.read_bytes()

            parsed = extract_text_from_pdf(content)

            text = parsed["text"]
            pages = parsed["total_pages"]

            if not text.strip():
                raise ValueError(
                    "This PDF does not contain extractable text."
                )

            chunk_count = index_document(
                document_id,
                document["filename"],
                text
            )

            update_document(
                document_id,
                status="ready",
                pages=pages,
                chunks=chunk_count,
                error=None
            )

        except Exception as exc:
            logger.exception(
                "Failed to index document %s", document_id
            )

            delete_vectors(document_id)

            update_document(
                document_id,
                status="failed",
                error=str(exc)[:250]
            )


@app.get("/")
def root():
    return {
        "name": "Enterprise AI Knowledge Assistant",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/documents")
def documents():
    return {
        "documents": [
            public_document(doc)
            for doc in list_documents()
        ]
    }


@app.get("/documents/{document_id}")
def document_detail(document_id: str):
    doc = get_document(document_id)

    if not doc:
        raise HTTPException(404, "Document not found.")

    return public_document(doc)


@app.post("/upload", status_code=202)
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    filename = Path(file.filename or "").name

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    document_id = str(uuid4())
    stored_path = UPLOAD_DIR / f"{document_id}.pdf"

    total = 0

    try:
        with stored_path.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)

                if total > MAX_UPLOAD:
                    raise HTTPException(
                        413,
                        "PDF exceeds the 10 MB limit."
                    )

                output.write(chunk)

        with stored_path.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise HTTPException(400, "Invalid PDF file.")

        create_document(
            document_id,
            filename,
            stored_path
        )

    except Exception:
        stored_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()

    background_tasks.add_task(
        process_document,
        document_id
    )

    return {
        "status": "queued",
        "document_id": document_id,
        "filename": filename,
        "message": "Upload complete. Indexing queued."
    }


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    # If indexing is in progress, this waits for that
    # particular index operation to finish safely.
    with index_lock:
        document = get_document(document_id)

        if not document:
            raise HTTPException(404, "Document not found.")

        try:
            deleted_chunks = delete_vectors(document_id)

            Path(document["stored_path"]).unlink(
                missing_ok=True
            )

            remove_document(document_id)

            return {
                "status": "deleted",
                "document_id": document_id,
                "filename": document["filename"],
                "deleted_chunks": deleted_chunks
            }
        except Exception:
            logger.exception(
                "Failed deleting document %s", document_id
            )
            raise HTTPException(
                500,
                "Failed to delete document."
            )


@app.post("/search")
def search(request: SearchRequest):
    doc = get_document(request.document_id)

    if not doc:
        raise HTTPException(404, "Document not found.")

    if doc["status"] != "ready":
        raise HTTPException(409, "Document is not ready.")

    results = search_documents(
        request.query,
        request.top_k,
        request.document_id
    )

    return {
        "query": request.query,
        "results": results,
        "total_results": len(results)
    }


@app.post("/ask")
def ask(request: AskRequest):
    try:
        return generate_answer(
            question=request.question,
            top_k=request.top_k,
            document_id=request.document_id
        )

    except ValueError as exc:
        raise HTTPException(400, str(exc))

    except RuntimeError as exc:
        raise HTTPException(503, str(exc))

    except Exception:
        logger.exception("AI answer failed")
        raise HTTPException(
            500,
            "Could not generate the answer."
        )