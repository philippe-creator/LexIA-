from typing import Optional
from pydantic import BaseModel, Field, field_validator

def safe_url(url: Optional[str]) -> Optional[str]:
    """N'autorise que les schémas http(s) — bloque javascript:/data: dans les liens de citation."""
    if not url: return None
    if not (url.startswith("http://") or url.startswith("https://")): return None
    return url

class DemoRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)

class FeedbackRequest(BaseModel):
    feedback: Optional[str] = None  # "up" | "down" | None (annule le retour)

    @field_validator("feedback")
    @classmethod
    def _validate_feedback(cls, v):
        if v not in (None, "up", "down"):
            raise ValueError("feedback doit être 'up', 'down' ou null")
        return v

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)
    conversation_id: Optional[str] = None
    domain: Optional[str] = None
    doc_type: Optional[str] = None
    year: Optional[int] = None
    lang: str = "fr"  # langue de réponse : "fr" | "ar"
    top_k: int = Field(5, ge=1, le=10)
    adapt_to_profile: bool = True

    @field_validator("lang")
    @classmethod
    def _validate_lang(cls, v):
        return v if v in ("fr", "ar") else "fr"

class Citation(BaseModel):
    index: int
    label: str
    domain: str
    source: str
    filename: str
    page: Optional[int] = None
    url: Optional[str] = None
    excerpt: str
    score: float
    retrieval_method: Optional[str] = None

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v):
        return safe_url(v)

class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    domains_searched: list[str]
    query: str
    conversation_id: str
    message_id: str
    confidence_score: float
    confidence_label: str
    adapted_for_role: Optional[str] = None
    suggested_queries: list[str] = []

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2)
    domains: Optional[list[str]] = None
    doc_type: Optional[str] = None
    year: Optional[int] = None
    top_k: int = Field(5, ge=1, le=20)

class SearchResult(BaseModel):
    text: str
    metadata: dict
    domain: str
    method: str
    score: float

class SearchResponse(BaseModel):
    results: list[SearchResult]
    domains_searched: list[str]
    total: int

class ReferenceRequest(BaseModel):
    reference: str = Field(..., min_length=2)
    domain: Optional[str] = None
    top_k: int = Field(5, ge=1, le=10)

class SnapshotInfo(BaseModel):
    id: str
    filename: str
    created_at: str
    char_count: int

class CompareRequest(BaseModel):
    snapshot_id_1: str
    snapshot_id_2: str

class WatchStatus(BaseModel):
    last_run: Optional[str]
    sources: list[dict]
    new_documents_count: int

class CorpusStats(BaseModel):
    stats: dict
    total_chunks: int
