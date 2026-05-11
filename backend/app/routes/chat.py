import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.config import settings
from app.llm import ollama
from app.models import ChatRequest
from app.rag import query
from app.security import require_api_key


router = APIRouter()


SYSTEM_PROMPT = (
    "Je bent een behulpzame, beknopte assistent. Antwoord standaard in het Nederlands, "
    "tenzij de gebruiker een andere taal gebruikt. "
    "Als 'Kennisbank-context' wordt meegegeven, gebruik die als primaire bron en "
    "verwijs naar de bron-documenten met hun naam. "
    "Verzin nooit feiten. Als je iets niet zeker weet of het niet in de context staat, "
    "zeg dat dan eerlijk."
)


@router.post("/chat", dependencies=[Depends(require_api_key)])
async def chat(req: ChatRequest):
    user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), "")

    context_block = ""
    sources: list[dict] = []
    if req.use_kb and user_msg:
        hits = await query(user_msg, top_k=settings.top_k)
        if hits:
            context_block = "\n\n".join(
                f"[bron: {h['metadata'].get('doc_name', 'onbekend')}]\n{h['text']}"
                for h in hits
            )
            sources = [
                {
                    "doc_name": h["metadata"].get("doc_name", "onbekend"),
                    "distance": h["distance"],
                }
                for h in hits
            ]

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context_block:
        messages.append(
            {
                "role": "system",
                "content": f"Kennisbank-context (gebruik dit, citeer bronnen):\n{context_block}",
            }
        )
    messages.extend([{"role": m.role, "content": m.content} for m in req.messages])

    async def gen():
        yield json.dumps({"type": "sources", "data": sources}) + "\n"
        try:
            async for chunk in ollama.chat_stream(messages):
                yield json.dumps({"type": "token", "data": chunk}) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "data": str(e)}) + "\n"
            return
        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")
