import json
from typing import AsyncIterator

import httpx

from app.config import settings


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(settings.request_timeout_s))

    async def ensure_model(self, model: str) -> None:
        r = await self.client.post(f"{self.base_url}/api/show", json={"name": model})
        if r.status_code == 200:
            return
        async with self.client.stream(
            "POST", f"{self.base_url}/api/pull", json={"name": model}
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                err = data.get("error")
                if err:
                    raise RuntimeError(f"Ollama pull mislukt voor {model}: {err}")

    async def embed(self, text: str) -> list[float]:
        r = await self.client.post(
            f"{self.base_url}/api/embed",
            json={"model": settings.embedding_model, "input": text},
        )
        r.raise_for_status()
        data = r.json()
        embeddings = data.get("embeddings") or []
        if not embeddings:
            raise RuntimeError("Embedding-respons bevat geen vectors")
        return embeddings[0]

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json={"model": settings.llm_model, "messages": messages, "stream": True},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = data.get("message") or {}
                content = msg.get("content")
                if content:
                    yield content
                if data.get("done"):
                    break

    async def close(self) -> None:
        await self.client.aclose()


ollama = OllamaClient()
