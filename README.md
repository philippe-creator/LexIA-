# LexIA Maroc — Plateforme multi-RAG de veille juridique et réglementaire

Assistant juridique pour le **droit marocain**, fondé sur une architecture **multi-RAG**
(Retrieval-Augmented Generation) et un chatbot conversationnel qui répond en langage
naturel — en **français ou en arabe** — en citant précisément ses sources (texte,
article, page).

> Stage de fin d'année — Transformation Digitale Industrielle · Zenithsoft, Rabat
> N'Guémawen N'DJINILA — 2026

Le code du projet se trouve dans le dossier [`lawis-mg-final/`](lawis-mg-final/).

## Fonctionnalités

- **Chatbot juridique sourcé** : réponse structurée citant l'article, le document et la
  page exacts ; réponses en streaming, adaptées au profil (étudiant, particulier,
  juriste, avocat, entreprise).
- **Retrieval hybride** : expansion de requête + recherche dense (embeddings) + BM25 +
  fusion RRF + re-classement cross-encoder + score de confiance.
- **Multi-corpus** : une base vectorielle par domaine (travail, fiscal, sociétés,
  protection des données, jurisprudence).
- **Audit de contrat** : upload d'un contrat → rapport de conformité au droit du travail.
- **Comparaison de versions**, **recherche par référence exacte**, **calculateurs
  juridiques** (indemnité, préavis, salaire net).
- **Démo publique** sans compte, **filtres avancés** (type de document, année),
  **feedback 👍/👎**, **support de l'arabe (RTL)**.
- Sécurité : authentification JWT + rôles, rate limiting, en-têtes de sécurité.

## Stack

Python 3.11 · FastAPI · Chroma · sentence-transformers (`multilingual-e5-large`) ·
cross-encoder · BM25 · Groq / OpenRouter (LLM) · React 18 · Docker

## Démarrage rapide

```bash
# Backend
cd lawis-mg-final
python -m venv .venv && source .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env    # renseigner SECRET_KEY et une clé LLM (Groq/OpenRouter)
uvicorn api.main:app --reload --port 8000

# Frontend (autre terminal)
cd lawis-mg-final/frontend
npm install && npm start
```

Accès : Frontend `http://localhost:3000` — API `http://localhost:8000/docs`

## Tests

```bash
cd lawis-mg-final && pytest tests/ -v
```

## Avertissement

Les réponses fournies sont **informatives** et fondées sur les textes officiels indexés.
Elles ne constituent **pas un avis juridique professionnel**.
