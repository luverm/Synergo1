import re
from io import BytesIO

from pypdf import PdfReader

from app.config import settings


ALLOWED_EXTENSIONS = (".pdf", ".txt", ".md")


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="ignore")
    raise ValueError(f"Niet ondersteund formaat. Toegestaan: {', '.join(ALLOWED_EXTENSIONS)}")


def chunk_text(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    size = max(200, settings.chunk_size)
    overlap = min(max(0, settings.chunk_overlap), size - 50)
    step = size - overlap
    out: list[str] = []
    i = 0
    while i < len(text):
        out.append(text[i : i + size])
        i += step
    return out
