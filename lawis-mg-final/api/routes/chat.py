import json
import asyncio
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from loguru import logger
from core.database import get_db, SessionLocal, Conversation, Message
from api.core.dependencies import CurrentUser
from api.repositories.conversation_repo import ConversationRepository
from api.schemas.chat import ChatRequest, ChatResponse, Citation, FeedbackRequest, DemoRequest
from retrieval.hybrid_retriever import retrieve
from retrieval.reranker import confidence_label_for_score
from core.domains import DOMAINS
from processing.doc_type import DOC_TYPES
from generation.llm_client import generate, generate_stream
from generation.prompt_builder import build_prompt, format_citations, extract_suggested_queries

router = APIRouter(prefix="/chat", tags=["Chatbot"])

# Content-Encoding: identity → indique à GZipMiddleware de ne PAS compresser ce
# flux. La compression bufferise les événements SSE (délivrance non temps réel) et
# peut retarder la fermeture de la connexion — ce qui laisserait le client bloqué
# en attente de la fin du flux.
_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive", "Content-Encoding": "identity"}
_NO_CONTEXT_ANSWER = (
    "Aucun texte juridique pertinent n'a été trouvé dans les corpus disponibles pour cette question. "
    "Essayez de préciser le domaine concerné (travail, fiscal, sociétés, données personnelles) ou de reformuler "
    "avec des termes plus spécifiques. Pour une recherche officielle directe : www.sgg.gov.ma, www.tax.gov.ma ou www.cndp.ma."
)

def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

# Démo publique (sans compte) : quota strict par IP et par jour, en plus du
# rate-limit global. But : vitrine sur la page d'accueil (cf. Adala/Al Mohami)
# sans exposer l'API LLM à un abus anonyme illimité.
_DEMO_LIMIT_PER_DAY = 5
_demo_usage: dict[str, tuple[str, int]] = {}  # ip -> (jour ISO, nb utilisé)

def _demo_consume_quota(ip: str) -> int:
    """Consomme une question de démo pour cette IP et retourne le nombre restant
    (>= 0). Retourne -1 sans rien consommer si le quota du jour est épuisé."""
    today = date.today().isoformat()
    day, count = _demo_usage.get(ip, (today, 0))
    if day != today:
        count = 0  # réinitialisation quotidienne
    if count >= _DEMO_LIMIT_PER_DAY:
        _demo_usage[ip] = (today, count)
        return -1
    count += 1
    _demo_usage[ip] = (today, count)
    return _DEMO_LIMIT_PER_DAY - count

@router.post("/demo")
async def chat_demo(request: DemoRequest, http_request: Request):
    """Chat de démonstration public (sans authentification, sans persistance).
    Réutilise le même pipeline retrieval + génération que /chat/, mais en profil
    'particulier', sans historique, sans filtres, et avec un quota quotidien."""
    ip = http_request.client.host if http_request.client else "unknown"
    remaining = _demo_consume_quota(ip)
    if remaining < 0:
        raise HTTPException(429, f"Limite de {_DEMO_LIMIT_PER_DAY} questions par jour atteinte pour la démo. Créez un compte gratuit pour continuer sans limite.")
    loop = asyncio.get_event_loop()
    chunks, conf_score, conf_label, domains_searched = await loop.run_in_executor(
        None, lambda: retrieve(query=request.query, top_k=4, user_id=None)
    )
    if not chunks:
        return {"answer": _NO_CONTEXT_ANSWER, "citations": [], "confidence_label": "insuffisant", "domains_searched": domains_searched, "remaining": remaining}
    system_prompt, user_message = build_prompt(request.query, chunks, user_role="particulier")
    try:
        raw = await loop.run_in_executor(None, lambda: generate(system_prompt, user_message))
    except Exception as e:
        logger.error(f"Erreur démo : {e}")
        raise HTTPException(503, "Le service de génération est momentanément indisponible. Réessayez.")
    answer, _ = extract_suggested_queries(raw)
    return {"answer": answer, "citations": format_citations(chunks), "confidence_label": conf_label, "domains_searched": domains_searched, "remaining": remaining}

def _validate_filters(request: ChatRequest):
    if request.domain and request.domain not in DOMAINS:
        raise HTTPException(400, f"Domaine invalide : {request.domain}")
    if request.doc_type and request.doc_type not in DOC_TYPES:
        raise HTTPException(400, f"Type de document invalide : {request.doc_type} (attendu : {', '.join(DOC_TYPES)})")

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: CurrentUser, db: Session = Depends(get_db)):
    _validate_filters(request)
    try:
        logger.info(f"Chat [{current_user.role}]: {request.query[:60]}")
        repo = ConversationRepository(db)
        conv = repo.get_or_create(current_user.id, request.conversation_id, request.query)
        repo.add_message(conv.id, "user", request.query)
        history, _ = repo.get_history(conv.id, 8)
        history = [{"role": m.role, "content": m.content} for m in history][:-1]
        domains = [request.domain] if request.domain else None
        chunks, conf_score, conf_label, domains_searched = retrieve(query=request.query, top_k=request.top_k, forced_domains=domains, user_id=current_user.id, doc_type=request.doc_type, year=request.year)
        if not chunks:
            answer = _NO_CONTEXT_ANSWER
            msg = repo.add_message(conv.id, "assistant", answer, citations=[], domains_searched=domains_searched, confidence_score=0.0)
            return ChatResponse(answer=answer, citations=[], domains_searched=domains_searched, query=request.query, conversation_id=conv.id, message_id=msg.id, confidence_score=0.0, confidence_label="insuffisant")
        role = current_user.role if request.adapt_to_profile else "particulier"
        system_prompt, user_message = build_prompt(request.query, chunks, user_role=role, conversation_history=history, lang=request.lang)
        raw = generate(system_prompt, user_message)
        answer, suggested = extract_suggested_queries(raw)
        raw_citations = format_citations(chunks)
        citations = [Citation(**c) for c in raw_citations]
        msg = repo.add_message(conv.id, "assistant", answer, citations=raw_citations, domains_searched=domains_searched, confidence_score=conf_score, retrieval_method="hybrid_rrf_rerank")
        if not conv.domain and domains_searched: conv.domain = domains_searched[0]; db.commit()
        return ChatResponse(answer=answer, citations=citations, domains_searched=domains_searched, query=request.query, conversation_id=conv.id, message_id=msg.id, confidence_score=conf_score, confidence_label=conf_label, adapted_for_role=role, suggested_queries=suggested)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur chat : {e}", exc_info=True)
        raise HTTPException(500, "Une erreur interne est survenue. Réessayez plus tard.")

@router.post("/stream")
async def chat_stream(request: ChatRequest, current_user: CurrentUser, db: Session = Depends(get_db)):
    """Variante streaming (SSE) de /chat/ — les tokens sont émis au fur et à mesure.

    Événements SSE (`data: {json}`) :
      - {"type":"meta", ...}   citations, domaines, confiance (envoyé une fois au début)
      - {"type":"token", "content": "..."}   fragment de réponse
      - {"type":"done", "message_id": "...", "suggested_queries": [...]}
      - {"type":"error", "detail": "..."}   en cas d'échec de génération
    """
    _validate_filters(request)
    logger.info(f"Chat stream [{current_user.role}]: {request.query[:60]}")
    repo = ConversationRepository(db)
    conv = repo.get_or_create(current_user.id, request.conversation_id, request.query)
    repo.add_message(conv.id, "user", request.query)
    history, _ = repo.get_history(conv.id, 8)
    history = [{"role": m.role, "content": m.content} for m in history][:-1]
    domains = [request.domain] if request.domain else None
    conv_id = conv.id
    role = current_user.role if request.adapt_to_profile else "particulier"
    # Le retrieval est bloquant (embeddings/BM25/rerank) — on le sort de la boucle
    # événementielle pour ne pas la geler pendant ~2 s.
    loop = asyncio.get_event_loop()
    chunks, conf_score, conf_label, domains_searched = await loop.run_in_executor(
        None, lambda: retrieve(query=request.query, top_k=request.top_k, forced_domains=domains, user_id=current_user.id, doc_type=request.doc_type, year=request.year)
    )

    if not chunks:
        msg = repo.add_message(conv_id, "assistant", _NO_CONTEXT_ANSWER, citations=[], domains_searched=domains_searched, confidence_score=0.0)
        msg_id = msg.id
        def empty_stream():
            yield _sse({"type": "meta", "conversation_id": conv_id, "citations": [], "domains_searched": domains_searched, "confidence_score": 0.0, "confidence_label": "insuffisant", "adapted_for_role": role})
            yield _sse({"type": "token", "content": _NO_CONTEXT_ANSWER})
            yield _sse({"type": "done", "message_id": msg_id, "suggested_queries": []})
        return StreamingResponse(empty_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)

    raw_citations = format_citations(chunks)
    system_prompt, user_message = build_prompt(request.query, chunks, user_role=role, conversation_history=history, lang=request.lang)

    def event_stream():
        yield _sse({"type": "meta", "conversation_id": conv_id, "citations": raw_citations, "domains_searched": domains_searched, "confidence_score": conf_score, "confidence_label": conf_label, "adapted_for_role": role})
        full = ""
        try:
            for token in generate_stream(system_prompt, user_message):
                full += token
                yield _sse({"type": "token", "content": token})
        except Exception as e:
            logger.error(f"Erreur streaming chat : {e}")
            yield _sse({"type": "error", "detail": "La génération a échoué. Réessayez."})
            return
        answer, suggested = extract_suggested_queries(full)
        # Persistance via une session fraîche : ce générateur s'exécute dans un
        # thread du threadpool (Starlette), distinct de la session de la requête.
        msg_id = None
        db2 = SessionLocal()
        try:
            msg = ConversationRepository(db2).add_message(conv_id, "assistant", answer, citations=raw_citations, domains_searched=domains_searched, confidence_score=conf_score, retrieval_method="hybrid_rrf_rerank_stream")
            msg_id = msg.id
            conv2 = db2.query(Conversation).filter(Conversation.id == conv_id).first()
            if conv2 and not conv2.domain and domains_searched:
                conv2.domain = domains_searched[0]; db2.commit()
        except Exception as e:
            logger.error(f"Persistance message stream échouée : {e}")
        finally:
            db2.close()
        yield _sse({"type": "done", "message_id": msg_id, "suggested_queries": suggested})

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)

@router.get("/conversations")
async def list_conversations(current_user: CurrentUser, limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    repo = ConversationRepository(db)
    convs, total = repo.list_for_user(current_user.id, limit=limit, offset=offset)
    return {"items":[{"id":c.id,"title":c.title,"domain":c.domain,"message_count":len(c.messages),"created_at":c.created_at.isoformat(),"updated_at":c.updated_at.isoformat()} for c in convs],"total":total,"limit":limit,"offset":offset}

@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, current_user: CurrentUser, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    conv = ConversationRepository(db).get(conv_id, current_user.id)
    if not conv: raise HTTPException(404, "Conversation introuvable.")
    messages, total = ConversationRepository(db).get_history(conv.id, limit=limit, offset=offset)
    return {"id":conv.id,"title":conv.title,"domain":conv.domain,"created_at":conv.created_at.isoformat(),"messages":[{"id":m.id,"role":m.role,"content":m.content,"citations":m.citations or [],"confidence_score":m.confidence_score,"confidence_label":confidence_label_for_score(m.confidence_score) if m.confidence_score is not None else None,"feedback":m.feedback,"created_at":m.created_at.isoformat()} for m in messages],"total":total,"limit":limit,"offset":offset}

@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    if not ConversationRepository(db).delete(conv_id, current_user.id): raise HTTPException(404, "Conversation introuvable.")
    return {"message": "Supprimée."}

@router.post("/messages/{message_id}/feedback")
async def set_message_feedback(message_id: str, request: FeedbackRequest, current_user: CurrentUser, db: Session = Depends(get_db)):
    msg = ConversationRepository(db).set_feedback(message_id, current_user.id, request.feedback)
    if not msg:
        raise HTTPException(404, "Message introuvable.")
    return {"message_id": msg.id, "feedback": msg.feedback}

@router.get("/search-history")
async def search_history(current_user: CurrentUser, q: str, limit: int = 20, db: Session = Depends(get_db)):
    if not q or len(q.strip()) < 2:
        raise HTTPException(400, "Requête trop courte (min 2 caractères).")
    term = f"%{q.strip()}%"
    results = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == current_user.id, Message.content.ilike(term))
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    return [{"id": m.id, "conversation_id": m.conversation_id, "role": m.role, "content": m.content, "confidence_score": m.confidence_score, "created_at": m.created_at.isoformat()} for m in results]
