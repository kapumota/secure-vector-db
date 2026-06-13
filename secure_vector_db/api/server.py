from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from secure_vector_db import __version__
from secure_vector_db.api.auth import require_api_key
from secure_vector_db.api.rate_limit import RateLimitMiddleware
from secure_vector_db.database import SecureVectorDB
from secure_vector_db.errors import IntegrityError, RecordNotFoundError, SecureVectorDBError

DB_PATH_ENV = "SECURE_VECTOR_DB_PATH"
VECTOR_INDEX_ENV = "SECURE_VECTOR_DB_VECTOR_INDEX"
EMBEDDING_MODEL_ENV = "SECURE_VECTOR_DB_EMBEDDING_MODEL"
EMBEDDING_MODEL_NAME_ENV = "SECURE_VECTOR_DB_EMBEDDING_MODEL_NAME"
LEARNED_INDEX_ENV = "SECURE_VECTOR_DB_LEARNED_INDEX"
LEARNED_MAX_ERROR_ENV = "SECURE_VECTOR_DB_LEARNED_MAX_ERROR"
DEFAULT_DB_PATH = "secure_vector_db_api.sqlite"


def _configured_db_path() -> str:
    return os.environ.get(DB_PATH_ENV, DEFAULT_DB_PATH)


def _configured_vector_index() -> str:
    return os.environ.get(VECTOR_INDEX_ENV, "kd_tree")

def _configured_embedding_model() -> str:
    return os.environ.get(EMBEDDING_MODEL_ENV, "hash")

def _configured_embedding_model_name() -> str | None:
    return os.environ.get(EMBEDDING_MODEL_NAME_ENV)


def _configured_learned_index_enabled() -> bool:
    value = os.environ.get(LEARNED_INDEX_ENV, "false").strip().lower()
    return value in {"1", "true", "yes", "si"}


def _configured_learned_max_error() -> int:
    raw_value = os.environ.get(LEARNED_MAX_ERROR_ENV, "64")
    try:
        value = int(raw_value)
    except ValueError:
        return 64
    return max(0, value)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = _configured_db_path()
    app.state.db_path = db_path
    app.state.vector_index = _configured_vector_index()
    app.state.embedding_model = _configured_embedding_model()
    app.state.embedding_model_name = _configured_embedding_model_name()
    app.state.learned_index_enabled = _configured_learned_index_enabled()
    app.state.learned_max_error = _configured_learned_max_error()
    app.state.db = SecureVectorDB.open(
        db_path,
        vector_index=app.state.vector_index,
        embedding_model=app.state.embedding_model,
        embedding_model_name=app.state.embedding_model_name,
        learned_index_enabled=app.state.learned_index_enabled,
        learned_max_error=app.state.learned_max_error,
    )
    try:
        yield
    finally:
        app.state.db.close()


app = FastAPI(
    title="SecureVectorDB API",
    version=__version__,
    description=(
        "API protegida por API key para una base vectorial verificable con "
        "persistencia SQLite, B+ Tree, embeddings configurables, indice vectorial configurable, rate limiting y Merkle root."
    ),
    lifespan=lifespan,
)


class InsertRequest(BaseModel):
    record_id: int = Field(..., ge=0, description="ID entero no negativo")
    text: str = Field(..., min_length=1, description="Texto a indexar")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos JSON opcionales")


class ErrorResponse(BaseModel):
    error: str
    detail: str


def get_db(request: Request) -> SecureVectorDB:
    return request.app.state.db


def get_db_path(request: Request) -> str:
    return request.app.state.db_path


@app.exception_handler(SecureVectorDBError)
def handle_app_error(_, exc: SecureVectorDBError):
    status = 400
    if isinstance(exc, RecordNotFoundError):
        status = 404
    if isinstance(exc, IntegrityError):
        status = 409
    return JSONResponse(status_code=status, content={"error": exc.__class__.__name__, "detail": str(exc)})


@app.get("/health", tags=["system"])
def health(db: SecureVectorDB = Depends(get_db), db_path: str = Depends(get_db_path)):
    return {"status": "ok", "records": len(db.store), "root_hash": db.root_hash, "storage": db_path, "vector_index": db.vector_index.backend_name, "embedding_model": db.embedder.name, "embedding_dim": db.embedding_dim, "ordered_index": db.ordered_index_stats()}


@app.post(
    "/records",
    tags=["records"],
    dependencies=[Depends(require_api_key)],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
)
def insert_record(req: InsertRequest, db: SecureVectorDB = Depends(get_db)):
    rec = db.insert(req.record_id, req.text, req.metadata)
    return {"record": rec.to_dict(), "root_hash": db.root_hash}


@app.get(
    "/records/{record_id}",
    tags=["records"],
    dependencies=[Depends(require_api_key)],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_record(record_id: int, db: SecureVectorDB = Depends(get_db)):
    rec = db.search_by_id(record_id)
    if rec is None:
        raise RecordNotFoundError(f"record_id={record_id} no existe")
    return rec.to_dict()


@app.delete("/records/{record_id}", tags=["records"], dependencies=[Depends(require_api_key)], responses={401: {"model": ErrorResponse}})
def delete_record(record_id: int, db: SecureVectorDB = Depends(get_db)):
    return {"deleted": db.delete(record_id), "root_hash": db.root_hash}


@app.get("/range", tags=["query"], dependencies=[Depends(require_api_key)], responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}})
def range_query(start: int = Query(...), end: int = Query(...), db: SecureVectorDB = Depends(get_db)):
    return [r.to_dict() for r in db.search_by_range(start, end)]


@app.get("/search", tags=["query"], dependencies=[Depends(require_api_key)], responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}})
def semantic_search(q: str = Query(..., min_length=1), k: int = Query(3, ge=1), db: SecureVectorDB = Depends(get_db)):
    return [{"record": rec.to_dict(), "distance": dist} for rec, dist in db.semantic_search(q, k)]


@app.get("/verify", tags=["integrity"], dependencies=[Depends(require_api_key)], responses={401: {"model": ErrorResponse}})
def verify(db: SecureVectorDB = Depends(get_db)):
    return {"valid": db.verify_dataset(), "root_hash": db.root_hash, "computed_root_hash": db.compute_root_hash()}


@app.get("/indexes/ordered/stats", tags=["indexes"], dependencies=[Depends(require_api_key)], responses={401: {"model": ErrorResponse}})
def ordered_index_stats(db: SecureVectorDB = Depends(get_db)):
    return db.ordered_index_stats()


@app.post("/verify/assert", tags=["integrity"], dependencies=[Depends(require_api_key)], responses={401: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def assert_verify(db: SecureVectorDB = Depends(get_db)):
    db.assert_integrity()
    return {"valid": True, "root_hash": db.root_hash}


app.add_middleware(RateLimitMiddleware)
