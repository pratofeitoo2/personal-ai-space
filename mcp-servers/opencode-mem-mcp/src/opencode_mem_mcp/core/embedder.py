from __future__ import annotations

import json
import struct
from typing import Any

import httpx

OLLAMA_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text:137m-v1.5-fp16"
EMBED_DIMS = 768


def embed(text: str, model: str = EMBED_MODEL) -> list[float]:
    payload = {"model": model, "input": text}
    resp = httpx.post(OLLAMA_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["embeddings"][0]


def embed_batch(texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    payload = {"model": model, "input": texts}
    resp = httpx.post(OLLAMA_URL, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["embeddings"]


def pack(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def unpack(data: bytes) -> list[float]:
    return list(struct.unpack(f"{len(data) // 4}f", data))
