"""FastAPI server for OpenAI Privacy Filter (OPF).

Loads the model once at startup and keeps it in memory.
Exposes HTTP endpoints for PII redaction.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from opf._api import OPF, RedactionResult

logger = logging.getLogger("opf-server")

_redactor: OPF | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redactor
    device = os.environ.get("OPF_DEVICE", "cpu")
    output_mode = os.environ.get("OPF_OUTPUT_MODE", "typed")
    checkpoint = os.environ.get("OPF_CHECKPOINT", None)

    logger.info("Loading OPF model (device=%s, output_mode=%s) ...", device, output_mode)
    start = time.monotonic()
    _redactor = OPF(
        model=checkpoint,
        device=device,
        output_mode=output_mode,
    )
    _redactor.get_runtime()
    elapsed = time.monotonic() - start
    logger.info("Model loaded in %.1fs", elapsed)
    yield
    _redactor = None


app = FastAPI(
    title="OPF Privacy Filter Service",
    description="PII detection and redaction API powered by OpenAI Privacy Filter",
    version="0.1.0",
    lifespan=lifespan,
)


class RedactRequest(BaseModel):
    text: str = Field(..., description="Text to redact")


class RedactBatchRequest(BaseModel):
    texts: list[str] = Field(..., description="List of texts to redact")


class SpanOut(BaseModel):
    label: str
    start: int
    end: int
    text: str
    placeholder: str


class RedactResponse(BaseModel):
    schema_version: int
    text: str
    redacted_text: str
    detected_spans: list[SpanOut]
    summary: dict
    warning: str | None = None
    latency_ms: float


class RedactTextOnlyResponse(BaseModel):
    redacted_text: str
    latency_ms: float


class RedactBatchResponse(BaseModel):
    results: list[RedactResponse]
    total_latency_ms: float


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", model_loaded=_redactor is not None)


def _build_response(text: str, result, latency_ms: float) -> RedactResponse:
    if isinstance(result, str):
        return RedactResponse(
            schema_version=0, text=text, redacted_text=result,
            detected_spans=[], summary={}, latency_ms=latency_ms,
        )
    assert isinstance(result, RedactionResult)
    return RedactResponse(
        schema_version=result.schema_version,
        text=result.text,
        redacted_text=result.redacted_text,
        detected_spans=[
            SpanOut(label=s.label, start=s.start, end=s.end,
                    text=s.text, placeholder=s.placeholder)
            for s in result.detected_spans
        ],
        summary=result.summary,
        warning=result.warning,
        latency_ms=latency_ms,
    )


@app.post("/redact", response_model=RedactResponse)
def redact(req: RedactRequest):
    if _redactor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    start = time.perf_counter()
    result = _redactor.redact(req.text)
    latency_ms = (time.perf_counter() - start) * 1000.0
    return _build_response(req.text, result, latency_ms)


@app.post("/redact/text", response_model=RedactTextOnlyResponse)
def redact_text_only(req: RedactRequest):
    if _redactor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    start = time.perf_counter()
    result = _redactor.redact(req.text)
    latency_ms = (time.perf_counter() - start) * 1000.0
    redacted = result.redacted_text if isinstance(result, RedactionResult) else str(result)
    return RedactTextOnlyResponse(redacted_text=redacted, latency_ms=latency_ms)


@app.post("/redact/batch", response_model=RedactBatchResponse)
def redact_batch(req: RedactBatchRequest):
    if _redactor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    batch_start = time.perf_counter()
    results = []
    for text in req.texts:
        start = time.perf_counter()
        result = _redactor.redact(text)
        latency_ms = (time.perf_counter() - start) * 1000.0
        results.append(_build_response(text, result, latency_ms))
    total_latency_ms = (time.perf_counter() - batch_start) * 1000.0
    return RedactBatchResponse(results=results, total_latency_ms=total_latency_ms)
