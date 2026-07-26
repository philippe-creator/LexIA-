from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.database import get_db
from core.plans import list_plans_public, PLANS, DEFAULT_PLAN
from api.core.dependencies import CurrentUser
from services.billing import get_usage, activate_plan

router = APIRouter(prefix="/billing", tags=["Abonnement"])


class SubscribeRequest(BaseModel):
    plan: str  # clé d'offre, ex. "pro"


@router.get("/plans")
async def get_plans():
    """Grille d'offres (page tarifs). Accessible sans être une fonctionnalité payante."""
    return {"plans": list_plans_public(), "default": DEFAULT_PLAN}


@router.get("/me")
async def my_subscription(current_user: CurrentUser, db: Session = Depends(get_db)):
    """Offre courante + usage du mois de l'utilisateur connecté."""
    return get_usage(db, current_user)


@router.post("/subscribe")
async def subscribe(request: SubscribeRequest, current_user: CurrentUser, db: Session = Depends(get_db)):
    """Active une offre.

    ⚠️ Paiement SIMULÉ : l'activation est immédiate, sans encaissement. C'est ici
    que s'insérera l'appel au prestataire (Stripe/CMI) : créer une session de
    paiement, puis n'activer l'offre que sur confirmation (webhook). La mécanique
    d'offres/quotas en aval est déjà complète et ne changera pas.
    """
    if request.plan not in PLANS:
        raise HTTPException(400, f"Offre inconnue : {request.plan}")
    usage = activate_plan(db, current_user, request.plan)
    return {"status": "activé", "simulated_payment": True, **usage}


@router.post("/cancel")
async def cancel(current_user: CurrentUser, db: Session = Depends(get_db)):
    """Résilie : retour à l'offre gratuite."""
    usage = activate_plan(db, current_user, DEFAULT_PLAN)
    return {"status": "résilié", **usage}
