import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, User
from core.plans import get_plan, plan_has_feature, monthly_quota, list_plans_public, \
    FEATURE_CONTRACT_AUDIT, FEATURE_CHAT
from services.billing import get_usage, consume_question, activate_plan
from fastapi import HTTPException


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


@pytest.fixture
def user(db):
    u = User(email="u@x.ma", username="u", hashed_password="x", plan="free", questions_used=0, usage_period_start=datetime.utcnow())
    db.add(u); db.commit()
    return u


# ── Registre des offres ────────────────────────────────────────────────────
def test_plans_registry():
    assert monthly_quota("free") == 20
    assert monthly_quota("pro") is None            # illimité
    assert plan_has_feature("pro", FEATURE_CONTRACT_AUDIT)
    assert not plan_has_feature("free", FEATURE_CONTRACT_AUDIT)
    assert plan_has_feature("free", FEATURE_CHAT)   # le chat reste gratuit

def test_unknown_plan_falls_back_to_free():
    assert get_plan("inexistant")["key"] == "free"

def test_list_plans_serializable():
    plans = list_plans_public()
    assert {p["key"] for p in plans} == {"free", "pro"}
    for p in plans:
        assert isinstance(p["features"], list)      # sets → listes (JSON)


# ── Usage & quota ──────────────────────────────────────────────────────────
def test_free_user_quota_enforced(db, user):
    for _ in range(20):
        consume_question(db, user)                  # 20 autorisées
    with pytest.raises(HTTPException) as e:
        consume_question(db, user)                  # la 21e est bloquée
    assert e.value.status_code == 402

def test_pro_user_is_unlimited(db, user):
    activate_plan(db, user, "pro")
    for _ in range(50):
        consume_question(db, user)                  # aucune limite
    assert get_usage(db, user)["unlimited"] is True

def test_usage_reporting(db, user):
    consume_question(db, user)
    consume_question(db, user)
    u = get_usage(db, user)
    assert u["plan"] == "free" and u["questions_used"] == 2 and u["questions_remaining"] == 18

def test_monthly_reset(db, user):
    user.questions_used = 20
    user.usage_period_start = datetime(2020, 1, 1)   # période révolue
    db.commit()
    # Une nouvelle question dans un mois différent réinitialise le compteur.
    consume_question(db, user)
    assert user.questions_used == 1

def test_subscribe_then_cancel(db, user):
    activate_plan(db, user, "pro")
    assert user.plan == "pro"
    activate_plan(db, user, "free")
    assert user.plan == "free"
