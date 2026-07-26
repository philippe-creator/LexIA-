"""
Facturation / usage — logique de l'abonnement freemium.

Mesure le nombre de questions consommées par mois et par utilisateur, applique le
quota de l'offre, et gère l'activation/résiliation. Le paiement réel n'est pas
branché : `activate_plan` fait foi d'un règlement réussi et sera appelé par le
webhook du prestataire (Stripe/CMI) une fois l'intégration faite. Rien d'autre
ne change à ce moment-là — toute la mécanique de quota/verrouillage est ici.
"""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from core.database import User
from core.plans import get_plan, monthly_quota, DEFAULT_PLAN, PLANS


def _same_period(a: datetime, b: datetime) -> bool:
    """Deux dates dans le même mois calendaire (période de facturation)."""
    return a.year == b.year and a.month == b.month


def _ensure_current_period(db: Session, user: User) -> None:
    """Réinitialise le compteur au changement de mois. Idempotent."""
    now = datetime.utcnow()
    start = user.usage_period_start
    if start is None or not _same_period(start, now):
        user.questions_used = 0
        user.usage_period_start = now
        db.commit()


def get_usage(db: Session, user: User) -> dict:
    """État d'usage courant : offre, quota, consommation, reste."""
    _ensure_current_period(db, user)
    plan_key = user.plan or DEFAULT_PLAN
    quota = monthly_quota(plan_key)
    used = user.questions_used or 0
    return {
        "plan": plan_key,
        "plan_label": get_plan(plan_key)["label"],
        "monthly_questions": quota,           # None = illimité
        "questions_used": used,
        "questions_remaining": None if quota is None else max(quota - used, 0),
        "unlimited": quota is None,
        "period_start": (user.usage_period_start or datetime.utcnow()).isoformat(),
    }


def consume_question(db: Session, user: User) -> None:
    """Décompte une question. Lève 402 si le quota mensuel est épuisé.

    402 Payment Required : le front l'interprète comme « il faut passer Pro ».
    """
    _ensure_current_period(db, user)
    quota = monthly_quota(user.plan or DEFAULT_PLAN)
    if quota is not None and (user.questions_used or 0) >= quota:
        raise HTTPException(
            status_code=402,
            detail=(f"Vous avez atteint votre quota de {quota} questions ce mois-ci. "
                    f"Passez à l'offre Pro pour des questions illimitées."),
        )
    user.questions_used = (user.questions_used or 0) + 1
    db.commit()


def activate_plan(db: Session, user: User, plan_key: str) -> dict:
    """Active une offre pour l'utilisateur (appelé après règlement — simulé ici)."""
    if plan_key not in PLANS:
        raise HTTPException(400, f"Offre inconnue : {plan_key}")
    user.plan = plan_key
    # Repartir sur une période neuve à l'activation (nouvel accès plein).
    user.questions_used = 0
    user.usage_period_start = datetime.utcnow()
    db.commit()
    return get_usage(db, user)
