# LexIA Maroc v2.0 — Plateforme SaaS de veille juridique

> Stage de fin d'année — Transformation Digitale Industrielle
> Zenithsoft, Rabat | N'Guémawen N'DJINILA | 2026

Plateforme de veille juridique pour le droit marocain basée sur une architecture **multi-RAG** (retrieval hybride dense + BM25 + reranking) avec **LLM via OpenRouter** (aucune installation lourde requise).

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
#    SECRET_KEY         (générer : python -c "import secrets; print(secrets.token_hex(32))")
#    OPENROUTER_API_KEY (obtenir sur https://openrouter.ai/keys — gratuit)

# 3. Lancer
docker-compose up --build

# 4. Ingestion initiale (dans un 2e terminal)
docker-compose exec api python ingestion/watcher.py
```

Accès : Frontend http://localhost:3000 — API http://localhost:8000/docs

## Démarrage sans Docker

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # remplir SECRET_KEY et OPENROUTER_API_KEY

# API
uvicorn api.main:app --reload --port 8000
# Frontend (autre terminal)
cd frontend && npm install && npm start
```

## Pourquoi OpenRouter ?
OpenRouter donne accès à des centaines de modèles (Mistral, LLaMA, Gemma...) via une seule clé API, **sans télécharger de modèle lourd ni GPU**. Des modèles gratuits sont disponibles (`mistralai/mistral-7b-instruct:free`). Configurable dans `.env` via `OPENROUTER_MODEL`.

## Stack
Python 3.11 · FastAPI · SQLAlchemy · Chroma · sentence-transformers · BM25 · OpenRouter · React 18 · Docker

## Tests
```bash
pytest tests/ -v
```

## Production
Changer dans `.env` : `SECRET_KEY`, `DEBUG=false`, `ENVIRONMENT=production`, `DATABASE_URL=postgresql://...`, `CORS_ORIGINS=https://votre-domaine.ma`
