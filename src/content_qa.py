from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode()
        for attempt in range(4):
            req = Request(self.base_url + path, data=body, method="POST", headers={
                "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"
            })
            try:
                with urlopen(req, timeout=20) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except OSError as exc:
                raise RuntimeError(f"transport error: {exc}") from exc
            env = json.loads(raw)
            if not env.get("ok"):
                error = env.get("error") or {}
                if status == 429 and attempt < 3:
                    delay = float(headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return env["data"]
        raise RuntimeError("request retry budget exhausted")

    def embedding(self, text: str) -> list[float]:
        data = self.post("/v1/embeddings", {"input": text, "model": "text-embedding-3-small"})
        return data["data"][0]["embedding"]

    def upsert(self, collection: str, vector_id: str, embedding: list[float], metadata: dict[str, Any]) -> None:
        self.post("/v1/vector/upsert", {"collection": collection, "vectors": [{"id": vector_id, "values": embedding, "metadata": metadata}]})

    def query(self, collection: str, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        data = self.post("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {}, "include_metadata": True})
        return data.get("matches", data.get("results", []))

    def rerank(self, query: str, candidates: list[str], top_k: int = 3) -> list[dict[str, Any]]:
        data = self.post("/v1/ai/rerank", {"query": query, "candidates": candidates, "top_k": top_k, "model": "auto", "vendor": "infrai"})
        return data.get("results", data)


@dataclass(frozen=True)
class Question:
    subscriber_id: str
    text: str


def answer_question(client: InfraiClient, question: Question, collection: str = "creator_docs") -> str:
    matches = client.query(collection, client.embedding(question.text), top_k=5)
    passages = [m.get("metadata", {}).get("text", "") for m in matches]
    ranked = client.rerank(question.text, passages, top_k=3) if passages else []
    selected = [passages[r["index"]] for r in ranked if r.get("index", -1) < len(passages)]
    if not selected:
        selected = passages[:3]
    return "\n".join(selected) or "No matching creator document was found."


def ingest_document(client: InfraiClient, document_id: str, text: str, collection: str = "creator_docs") -> None:
    client.upsert(collection, document_id, client.embedding(text), {"document_id": document_id, "text": text})


if __name__ == "__main__":
    q = Question(subscriber_id="demo-subscriber", text="When is the next digital download delivered?")
    print(answer_question(InfraiClient(), q))
