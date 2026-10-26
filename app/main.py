from datetime import datetime, timezone

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)
from pydantic import BaseModel, Field

from app.pdf_processor import extract_text_from_pdf
from app.vector_store import (
    store_document,
    search_documents
)
from app.rag import generate_answer

from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Enterprise AI Knowledge Assistant",
    description="PDF-powered AI assistant with RAG",
    version="1.3.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
MAX_FILE_SIZE = 10 * 1024 * 1024


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)


@app.get("/")
def home():
    return {
        "application": "Enterprise AI Knowledge Assistant",
        "status": "running",
        "version": "1.3.0",
        "features": [
            "PDF upload",
            "Semantic search",
            "AI question answering"
        ]
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if (
        not file.filename
        or not file.filename.lower().endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    pdf_bytes = await file.read(MAX_FILE_SIZE + 1)
    await file.close()

    if len(pdf_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="PDF must be smaller than 10 MB."
        )

    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file."
        )

    try:
        result = extract_text_from_pdf(pdf_bytes)

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to read this PDF."
        )

    if not result["text"].strip():
        raise HTTPException(
            status_code=422,
            detail="No extractable text found in this PDF."
        )

    try:
        stored = store_document(
            filename=file.filename,
            text=result["text"]
        )

    except Exception as exc:
        print(f"Vector storage error: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Unable to index the PDF."
        )

    return {
        "filename": file.filename,
        "status": "success",
        "total_pages": result["total_pages"],
        "characters": len(result["text"]),
        "document_id": stored["document_id"],
        "chunks_stored": stored["chunks_stored"]
    }


@app.post("/search")
def search(request: SearchRequest):
    try:
        matches = search_documents(
            query=request.query,
            top_k=request.top_k
        )

    except Exception as exc:
        print(f"Search error: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Document search failed."
        )

    return {
        "query": request.query,
        "total_results": len(matches),
        "results": matches
    }


@app.post("/ask")
def ask_question(request: QuestionRequest):
    try:
        return generate_answer(
            question=request.question,
            top_k=request.top_k
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc)
        )

    except Exception as exc:
        print(f"RAG error: {type(exc).__name__}: {exc}")

        raise HTTPException(
            status_code=500,
            detail="AI answer generation failed. Check the server logs."
        )