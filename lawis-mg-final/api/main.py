import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from core.config import settings
from core.database import init_db
from api.middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware, RequestLoggingMiddleware
from api.routes.auth import router as auth_router
from api.routes.chat import router as chat_router
from api.routes.search_watch import search_router, watch_router
from api.routes.compare import router as compare_router
from api.routes.reference_search import router as reference_router
from api.routes.documents import router as documents_router
from api.routes.calculators import router as calculators_router
from api.routes.notifications import router as notifications_router
from api.routes.export import router as export_router
from api.routes.legal_documents import router as legal_documents_router
from api.routes.admin_users import router as admin_users_router


def _active_llm_key() -> str:
    return {"openai": settings.OPENAI_API_KEY, "gemini": settings.GEMINI_API_KEY, "openrouter": settings.OPENROUTER_API_KEY, "groq": settings.GROQ_API_KEY}.get(settings.LLM_PROVIDER.lower(), "")

def _active_llm_model() -> str:
    return {"openai": settings.OPENAI_MODEL, "gemini": settings.GEMINI_MODEL, "openrouter": settings.OPENROUTER_MODEL, "groq": settings.GROQ_MODEL}.get(settings.LLM_PROVIDER.lower(), "")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Démarrage LexIA Maroc v{settings.APP_VERSION}")
    if settings.SECRET_KEY == "CHANGE_ME":
        raise RuntimeError("SECRET_KEY n'a pas été configurée — générez-en une avec `python -c \"import secrets; print(secrets.token_hex(32))\"` et placez-la dans .env avant de démarrer.")
    for d in [settings.RAW_DATA_DIR,settings.PROCESSED_DATA_DIR,settings.UPLOADS_DIR,settings.LOGS_DIR,settings.CHROMA_PERSIST_DIR]:
        Path(d).mkdir(parents=True,exist_ok=True)
    init_db()
    logger.info("Base de données prête.")
    if not _active_llm_key():
        logger.warning(f"⚠️  Aucune clé configurée pour LLM_PROVIDER={settings.LLM_PROVIDER} — le chatbot ne fonctionnera pas.")
    # Préchauffage des modèles lourds (embedding + reranker) au démarrage plutôt
    # qu'à la première requête — évite ~10 s de latence sur la 1re question utilisateur.
    try:
        from processing.embedder import get_model
        from retrieval.reranker import get_reranker
        logger.info("Préchauffage des modèles ML…")
        get_model()
        get_reranker()
        logger.info("Modèles ML prêts.")
    except Exception as e:
        logger.warning(f"Préchauffage des modèles ignoré ({e}) — chargement à la première requête.")
    yield
    logger.info("Arrêt.")

_is_prod = settings.ENVIRONMENT == "production"
app = FastAPI(title="LexIA Maroc", description="Plateforme SaaS de veille juridique multi-RAG", version=settings.APP_VERSION, docs_url=None if _is_prod else "/docs", redoc_url=None if _is_prod else "/redoc", openapi_url=None if _is_prod else "/openapi.json", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(search_router)
app.include_router(watch_router)
app.include_router(compare_router)
app.include_router(reference_router)
app.include_router(documents_router)
app.include_router(calculators_router)
app.include_router(notifications_router)
app.include_router(export_router)
app.include_router(legal_documents_router)
app.include_router(admin_users_router)


@app.get("/", tags=["Health"])
async def root(): return {"service":"LexIA Maroc","version":settings.APP_VERSION,"status":"running","docs":"/docs"}

@app.get("/health", tags=["Health"])
async def health():
    from processing.indexer import get_corpus_stats
    stats=get_corpus_stats(); total=sum(stats.values())
    return {"status":"ok","corpus_stats":stats,"total_chunks":total,"corpus_ready":total>0,"llm_provider":settings.LLM_PROVIDER,"llm_configured":bool(_active_llm_key()),"llm_model":_active_llm_model()}

if __name__=="__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.DEBUG)
