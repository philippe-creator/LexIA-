from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from core.database import get_db, User, Conversation, Message
from api.core.dependencies import CurrentUser, require_role, require_owner
from api.repositories.user_repo import UserRepository

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/users")
async def list_users(current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [u.to_dict() for u in users]


@router.post("/users/{user_id}/promote")
async def promote_user(user_id: str, request: Request, current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Compte introuvable.")
    if user.role == "admin":
        raise HTTPException(400, "Ce compte est déjà admin.")
    previous_role = user.role
    user.role = "admin"
    db.commit()
    UserRepository(db).log_action(current_user.id, "promote_admin", resource=user.id, details={"email": user.email, "previous_role": previous_role}, ip=request.client.host if request.client else None)
    return user.to_dict()


@router.post("/users/{user_id}/demote")
async def demote_user(user_id: str, request: Request, current_user: User = Depends(require_owner), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Compte introuvable.")
    if user.id == current_user.id:
        raise HTTPException(400, "Vous ne pouvez pas vous rétrograder vous-même.")
    if user.is_owner:
        raise HTTPException(400, "Un propriétaire ne peut pas être rétrogradé depuis cette interface.")
    if user.role != "admin":
        raise HTTPException(400, "Ce compte n'est pas admin.")
    user.role = "particulier"
    db.commit()
    UserRepository(db).log_action(current_user.id, "demote_admin", resource=user.id, details={"email": user.email}, ip=request.client.host if request.client else None)
    return user.to_dict()


@router.get("/overview")
async def overview(current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Statistiques d'usage pour le tableau de bord — nombre de comptes,
    activité récente, domaines les plus demandés. Accessible à tout admin
    (pas réservé au propriétaire, contrairement à la gestion des comptes)."""
    total_users = db.query(func.count(User.id)).scalar()
    verified_users = db.query(func.count(User.id)).filter(User.email_verified == True).scalar()
    admin_count = db.query(func.count(User.id)).filter(User.role == "admin").scalar()

    since_7d = datetime.utcnow() - timedelta(days=7)
    messages_7d = db.query(func.count(Message.id)).filter(Message.created_at >= since_7d).scalar()
    since_30d = datetime.utcnow() - timedelta(days=30)
    messages_30d = db.query(func.count(Message.id)).filter(Message.created_at >= since_30d).scalar()

    domain_rows = (
        db.query(Conversation.domain, func.count(Conversation.id))
        .filter(Conversation.domain.isnot(None))
        .group_by(Conversation.domain)
        .order_by(func.count(Conversation.id).desc())
        .limit(6)
        .all()
    )
    top_domains = [{"domain": d, "count": c} for d, c in domain_rows]

    # Qualité des réponses : seuils identiques à confidence_label_for_score()
    # (retrieval/reranker.py) — pas réutilisable telle quelle en SQL, donc
    # répliquée ici via CASE plutôt que de charger tous les messages en Python.
    label_expr = case(
        (Message.confidence_score >= 0.8, "élevé"),
        (Message.confidence_score >= 0.6, "moyen"),
        (Message.confidence_score >= 0.4, "faible"),
        else_="insuffisant",
    )
    confidence_rows = (
        db.query(label_expr.label("label"), func.count(Message.id))
        .filter(Message.role == "assistant", Message.confidence_score.isnot(None))
        .group_by("label")
        .all()
    )
    confidence_distribution = {label: count for label, count in confidence_rows}
    total_answered = sum(confidence_distribution.values())
    avg_confidence = db.query(func.avg(Message.confidence_score)).filter(
        Message.role == "assistant", Message.confidence_score.isnot(None)
    ).scalar()
    insufficient_rate_pct = (
        round(100 * confidence_distribution.get("insuffisant", 0) / total_answered, 1) if total_answered else None
    )

    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "admin_count": admin_count,
        "messages_last_7d": messages_7d,
        "messages_last_30d": messages_30d,
        "top_domains": top_domains,
        "avg_confidence_score": round(avg_confidence, 2) if avg_confidence is not None else None,
        "insufficient_rate_pct": insufficient_rate_pct,
        "confidence_distribution": confidence_distribution,
        "total_answered": total_answered,
    }
