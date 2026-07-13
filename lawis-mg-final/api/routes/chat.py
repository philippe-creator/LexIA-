import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from loguru import logger
from core.database import get_db, SessionLocal, Conversation
from api.core.dependencies import CurrentUser
from api.repositories.conversation_repo import ConversationRepository
from api.schemas.chat import ChatRequest, ChatResponse, Citation
from retrieval.hybrid_retriever import retrieve
from retrieval.reranker import confidence_label_for_score
from core.domains import DOMAINS
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

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: CurrentUser, db: Session = Depends(get_db)):
    if request.domain and request.domain not in DOMAINS:
        raise HTTPException(400, f"Domaine invalide : {request.domain}")
    try:
        logger.info(f"Chat [{current_user.role}]: {request.query[:60]}")
        repo = ConversationRepository(db)
        conv = repo.get_or_create(current_user.id, request.conversation_id, request.query)
        repo.add_message(conv.id, "user", request.query)
        history = [{"role": m.role, "content": m.content} for m in repo.get_history(conv.id, 8)[:-1]]
        domains = [request.domain] if request.domain else None
        chunks, conf_score, conf_label, domains_searched = retrieve(query=request.query, top_k=request.top_k, forced_domains=domains, user_id=current_user.id)
        if not chunks:
            answer = _NO_CONTEXT_ANSWER
            msg = repo.add_message(conv.id, "assistant", answer, citations=[], domains_searched=domains_searched, confidence_score=0.0)
            return ChatResponse(answer=answer, citations=[], domains_searched=domains_searched, query=request.query, conversation_id=conv.id, message_id=msg.id, confidence_score=0.0, confidence_label="insuffisant")
        role = current_user.role if request.adapt_to_profile else "particulier"
        system_prompt, user_message = build_prompt(request.query, chunks, user_role=role, conversation_history=history)
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
    if request.domain and request.domain not in DOMAINS:
        raise HTTPException(400, f"Domaine invalide : {request.domain}")
    logger.info(f"Chat stream [{current_user.role}]: {request.query[:60]}")
    repo = ConversationRepository(db)
    conv = repo.get_or_create(current_user.id, request.conversation_id, request.query)
    repo.add_message(conv.id, "user", request.query)
    history = [{"role": m.role, "content": m.content} for m in repo.get_history(conv.id, 8)[:-1]]
    domains = [request.domain] if request.domain else None
    conv_id = conv.id
    role = current_user.role if request.adapt_to_profile else "particulier"
    # Le retrieval est bloquant (embeddings/BM25/rerank) — on le sort de la boucle
    # événementielle pour ne pas la geler pendant ~2 s.
    loop = asyncio.get_event_loop()
    chunks, conf_score, conf_label, domains_searched = await loop.run_in_executor(
        None, lambda: retrieve(query=request.query, top_k=request.top_k, forced_domains=domains, user_id=current_user.id)
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
    system_prompt, user_message = build_prompt(request.query, chunks, user_role=role, conversation_history=history)

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
async def list_conversations(current_user: CurrentUser, limit: int = 20, db: Session = Depends(get_db)):
    convs = ConversationRepository(db).list_for_user(current_user.id, limit=limit)
    return [{"id":c.id,"title":c.title,"domain":c.domain,"message_count":len(c.messages),"created_at":c.created_at.isoformat(),"updated_at":c.updated_at.isoformat()} for c in convs]

@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    conv = ConversationRepository(db).get(conv_id, current_user.id)
    if not conv: raise HTTPException(404, "Conversation introuvable.")
    # confidence_label n'est pas persisté (seul le score l'est) — on le redérive
    # du score enregistré, avec les mêmes seuils que la génération live.
    return {"id":conv.id,"title":conv.title,"domain":conv.domain,"created_at":conv.created_at.isoformat(),"messages":[{"id":m.id,"role":m.role,"content":m.content,"citations":m.citations or [],"confidence_score":m.confidence_score,"confidence_label":confidence_label_for_score(m.confidence_score) if m.confidence_score is not None else None,"created_at":m.created_at.isoformat()} for m in conv.messages]}

@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    if not ConversationRepository(db).delete(conv_id, current_user.id): raise HTTPException(404, "Conversation introuvable.")
    return {"message": "Supprimée."}
