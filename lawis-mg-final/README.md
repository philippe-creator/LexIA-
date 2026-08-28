# LexIA Maroc v2.0 — Plateforme SaaS de veille juridique

> Stage de fin d'année — Transformation Digitale Industrielle
> Zenithsoft, Rabat | N'Guémawen N'DJINILA | 2026

Plateforme de veille juridique pour le droit marocain basée sur une architecture **multi-RAG** (retrieval hybride dense + BM25 + reranking) avec **LLM via Groq** (gratuit, inférence rapide — aucun modèle lourd à héberger côté génération).

## Fonctionnalités
- Chatbot juridique adaptatif selon le profil (étudiant / juriste / avocat / entreprise / particulier)
- Mémoire conversationnelle persistée par utilisateur
- Retrieval hybride : query expansion + dense + BM25 + fusion RRF + reranking cross-encoder + score de confiance
- Recherche par référence exacte (loi 09-08, article 62, dahir 1-72-184)
- Comparaison de versions (CGI 2025 vs CGI 2026)
- Veille active des nouveaux textes
- Upload de documents utilisateur avec OCR
- Authentification JWT + RBAC + rate limiting

## Domaines couverts
Droit du travail, fiscal, sociétés, protection des données (loi 09-08), jurisprudence (Cour de cassation).

## Démarrage rapide (Docker)

```bash
# 1. Configurer
cp .env.example .env

# 2. Éditer .env — DEUX valeurs obligatoires :
#    SECRET_KEY    (générer : python -c "import secrets; print(secrets.token_hex(32))")
#    GROQ_API_KEY  (obtenir sur https://console.groq.com/keys — gratuit)

# 3. Lancer (Docker Desktop doit être démarré)
docker compose up --build -d

# 4. (si le corpus est vide) reconstruire depuis data/raw/
docker compose run --rm api python -m scripts.backfill_corpus
```

Accès : Frontend http://localhost:3000 — API http://localhost:8000/docs

> **Mise en production** (HTTPS, reverse proxy, PostgreSQL, check-list sécurité) :
> voir **[DEPLOYMENT.md](DEPLOYMENT.md)**.

## Démarrage sans Docker

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # remplir SECRET_KEY et GROQ_API_KEY

# API
uvicorn api.main:app --reload --port 8000
# Frontend (autre terminal)
cd frontend && npm install && npm start
```

## Fournisseur LLM
**Groq** est le fournisseur par défaut (`LLM_PROVIDER=groq`, `openai/gpt-oss-20b`) :
gratuit, inférence très rapide, aucune installation lourde côté génération. Une
cascade de secours (`GROQ_MODELS`) prend le relais en cas d'erreur récupérable.
OpenAI, Gemini et OpenRouter restent supportés comme fournisseurs alternatifs
(basculer via `LLM_PROVIDER` dans `.env`).

## Stack
Python 3.11 · FastAPI · SQLAlchemy · Chroma · sentence-transformers · BM25 · Groq · React 18 · Docker

## Tests
```bash
pytest tests/ -v
```

## Production
Voir le runbook complet : **[DEPLOYMENT.md](DEPLOYMENT.md)** (build & lancement
Docker, HTTPS/reverse proxy, PostgreSQL, initialisation du corpus, check-list
sécurité).
