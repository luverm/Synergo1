import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.llm import ollama
from app.routes import chat, kb


logger = logging.getLogger("synergo")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    for model in (settings.llm_model, settings.embedding_model):
        try:
            logger.info("Controleren / pullen Ollama model: %s", model)
            await ollama.ensure_model(model)
        except Exception as e:
            logger.warning("Kon model %s niet voorbereiden: %s", model, e)
    yield
    await ollama.close()


app = FastAPI(title="Synergo Local Chatbot", version="0.1.0", lifespan=lifespan)

origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(kb.router, prefix="/api/kb")


@app.get("/health")
async def health():
    return {"status": "ok", "llm_model": settings.llm_model, "embedding_model": settings.embedding_model}
