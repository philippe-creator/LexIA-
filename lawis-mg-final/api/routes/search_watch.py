import json, os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db, User
from api.core.dependencies import CurrentUser, require_role
from api.schemas.chat import SearchRequest, SearchResponse, SearchResult, WatchStatus, CorpusStats
from retrieval.hybrid_retriever import retrieve
from processing.indexer import get_corpus_stats
from core.domains import DOMAINS

search_router = APIRouter(prefix="/search", tags=["Recherche"])
watch_router = APIRouter(prefix="/watch", tags=["Veille"])
LOGS_DIR = Path(os.getenv("LOGS_DIR", "./logs"))

@search_router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest, current_user: CurrentUser):
    if request.domains:
        invalid = [d for d in request.domains if d not in DOMAINS]
        if invalid: raise HTTPException(400, f"Domaine(s) invalide(s) : {', '.join(invalid)}")
    chunks, _, _, domains_searched = retrieve(query=request.query, top_k=request.top_k, forced_domains=request.domains, user_id=current_user.id)
    results = [SearchResult(text=c["text"], metadata=c.get("metadata",{}), domain=c.get("domain","N/A"), method=c.get("method","hybrid"), score=float(c.get("rerank_score",c.get("rrf_score",c.get("score",0))))) for c in chunks]
    return SearchResponse(results=results, domains_searched=domains_searched, total=len(results))

@search_router.get("/stats", response_model=CorpusStats)
async def corpus_stats():
    stats = get_corpus_stats()
    return CorpusStats(stats=stats, total_chunks=sum(stats.values()))

@watch_router.get("/status", response_model=WatchStatus)
async def watch_status(current_user: CurrentUser):
    state_file = LOGS_DIR / "watch_state.json"
    if not state_file.exists(): return WatchStatus(last_run=None, sources=[], new_documents_count=0)
    state = json.loads(state_file.read_text(encoding="utf-8"))
    sources = [{"name":k,**v} for k,v in state.items()]
    last_run = max((s.get("last_check","") for s in sources), default=None)
    return WatchStatus(last_run=last_run, sources=sources, new_documents_count=sum(1 for s in sources if s.get("changed",False)))

@watch_router.post("/trigger")
async def trigger_watch(current_user: User = Depends(require_role("admin"))):
    from ingestion.watcher import run_watch_cycle
    import asyncio
    report = await asyncio.get_event_loop().run_in_executor(None, run_watch_cycle)
    return {"status":"completed","new_documents":len(report.get("new_documents",[]))}
