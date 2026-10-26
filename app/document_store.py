import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "documents.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def connection():
    con = sqlite3.connect(str(DATABASE), timeout=30)
    con.row_factory = sqlite3.Row
    return con


def now():
    return datetime.now(timezone.utc).isoformat()


def init_documents():
    with connection() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                status TEXT NOT NULL,
                pages INTEGER DEFAULT 0,
                chunks INTEGER DEFAULT 0,
                error TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Interrupted jobs can be retried by uploading the PDF again.
        db.execute("""
            UPDATE documents
            SET status = 'failed',
                error = 'Indexing was interrupted. Please upload again.'
            WHERE status IN ('queued', 'indexing')
        """)


def create_document(document_id, filename, path):
    with connection() as db:
        db.execute("""
            INSERT INTO documents (
                id, filename, stored_path, status, created_at
            )
            VALUES (?, ?, ?, 'queued', ?)
        """, (document_id, filename, str(path), now()))


def get_document(document_id):
    with connection() as db:
        row = db.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,)
        ).fetchone()

    return dict(row) if row else None


def list_documents():
    with connection() as db:
        rows = db.execute("""
            SELECT * FROM documents
            ORDER BY created_at DESC
        """).fetchall()

    return [dict(row) for row in rows]


def update_document(document_id, **fields):
    allowed = {"status", "pages", "chunks", "error"}
    fields = {k: v for k, v in fields.items() if k in allowed}

    if not fields:
        return

    assignments = ", ".join(f"{key} = ?" for key in fields)

    with connection() as db:
        db.execute(
            f"UPDATE documents SET {assignments} WHERE id = ?",
            [*fields.values(), document_id]
        )


def remove_document(document_id):
    with connection() as db:
        db.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,)
        )