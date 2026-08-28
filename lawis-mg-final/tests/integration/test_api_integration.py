import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, User, get_db
from api.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def _auth_headers():
    payload = {
        "email": "integration@lexia.ma",
        "password": "Integration1",
        "username": "integration",
    }
    r = client.post("/auth/register", json=payload)
    # La base in-memory est partagée entre les tests (StaticPool au niveau module) :
    # si l'utilisateur a déjà été créé par un test précédent, r vaut 400 et on
    # passe directement à la connexion.
    if r.status_code == 201:
        # /auth/register ne connecte plus automatiquement (confirmation email
        # requise, voir api/routes/auth.py) — en test, pas d'email réel envoyé :
        # on marque le compte vérifié directement en base, comme le ferait
        # normalement l'utilisateur en cliquant le lien reçu par email.
        db = TestingSessionLocal()
        db.query(User).filter(User.email == payload["email"]).update({"email_verified": True})
        db.commit()
        db.close()
    else:
        assert r.status_code == 400, r.text
    r = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_demo_chat():
    r = client.post("/chat/demo", json={"query": "Article 1"})
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "citations" in data


def test_auth_flow():
    headers = _auth_headers()
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "integration@lexia.ma"


def test_conversation_crud():
    headers = _auth_headers()
    r = client.get("/chat/conversations", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data

    r = client.post("/chat/", json={"query": "Qu'est-ce que le droit du travail ?"}, headers=headers)
    assert r.status_code == 200
    conv_id = r.json()["conversation_id"]

    r = client.get(f"/chat/conversations/{conv_id}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "messages" in data
    assert "total" in data

    r = client.delete(f"/chat/conversations/{conv_id}", headers=headers)
    assert r.status_code == 200


def test_search_and_watch_status():
    headers = _auth_headers()
    r = client.post("/search/", json={"query": " travail ", "top_k": 3}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "results" in data

    r = client.get("/watch/status", headers=headers)
    assert r.status_code == 200


def test_search_history():
    # Régression : la route utilisait Message sans l'importer → 500 NameError.
    headers = _auth_headers()
    r = client.get("/chat/search-history?q=licenciement", headers=headers)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)
