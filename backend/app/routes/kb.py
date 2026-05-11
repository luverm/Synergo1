import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import settings
from app.ingest import ALLOWED_EXTENSIONS, chunk_text, extract_text
from app.rag import add_chunks, delete_document, list_documents
from app.security import require_api_key


router = APIRouter()

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_DOC_ID = re.compile(r"^[a-f0-9]{32}$")


def _safe_filename(name: str) -> str:
    base = Path(name).name
    cleaned = _SAFE_NAME.sub("_", base).strip("._-")
    return cleaned[:200] or "document"


@router.post("/upload", dependencies=[Depends(require_api_key)])
async def upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Geen bestandsnaam meegegeven")

    safe = _safe_filename(file.filename)
    if not safe.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Niet ondersteund formaat. Toegestaan: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Bestand te groot (max {settings.max_upload_mb} MB)",
        )

    try:
        text = extract_text(safe, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Kon document niet inlezen: {e}",
        )

    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Geen tekst gevonden in document"
        )

    doc_id = uuid.uuid4().hex
    docs_dir = Path(settings.documents_path)
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / f"{doc_id}__{safe}").write_bytes(data)

    await add_chunks(doc_id, safe, chunks)
    return {"doc_id": doc_id, "doc_name": safe, "chunks": len(chunks)}


@router.get("/documents", dependencies=[Depends(require_api_key)])
async def documents():
    return list_documents()


@router.delete("/documents/{doc_id}", dependencies=[Depends(require_api_key)])
async def delete(doc_id: str):
    if not _DOC_ID.match(doc_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ongeldig document-id")
    n = delete_document(doc_id)
    docs_dir = Path(settings.documents_path)
    for p in docs_dir.glob(f"{doc_id}__*"):
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    return {"deleted_chunks": n}
