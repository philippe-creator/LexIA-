# Déploiement en production — LexIA Maroc

Guide de mise en production de la plateforme (API FastAPI + frontend React servi
par nginx + service de veille). La stack est entièrement conteneurisée.

---

## 1. Prérequis

- **Docker** + **Docker Compose v2** (`docker compose version`). Sur Windows/macOS,
  **Docker Desktop doit être démarré** (le moteur Linux doit tourner) avant tout `docker` — sinon
  `failed to connect to the docker API`.
- ~6 Go d'espace disque (l'image API embarque les modèles ML, ~2,2 Go).
- Une clé LLM valide (Groq recommandé — gratuit : https://console.groq.com/keys).
- Pour un déploiement exposé sur Internet : un nom de domaine + un reverse proxy
  HTTPS (voir §5). **HTTPS est obligatoire en production** (cf. cookies sécurisés, §4).

---

## 2. Configuration (`.env`)

```bash
cp .env.example .env
```

Renseigner **au minimum** :

| Variable | Valeur en production |
|---|---|
| `SECRET_KEY` | 64 hex — `python -c "import secrets; print(secrets.token_hex(32))"` (jamais la valeur d'exemple) |
| `ENVIRONMENT` | `production` (active les cookies `Secure`, désactive `/docs`, `/redoc`, `/openapi.json`) |
| `DEBUG` | `false` |
| `LLM_PROVIDER` + clé | `groq` + `GROQ_API_KEY=gsk_...` |
| `CORS_ORIGINS` | l'origine publique exacte du frontend, ex. `https://lexia.votre-domaine.ma` |
| `DATABASE_URL` | SQLite convient pour une instance unique ; PostgreSQL recommandé au-delà (§6) |

Le `.env` n'est **jamais** commité (il est dans `.gitignore` et `.dockerignore`). Au
démarrage, l'API **refuse de booter** si `SECRET_KEY` vaut encore `CHANGE_ME`.

---

## 3. Build & lancement

```bash
docker compose build          # ~15-30 min au 1er build (torch CPU + modèles 2,2 Go)
docker compose up -d
docker compose ps             # les 3 services doivent être "healthy"/"running"
```

Services démarrés :

| Service | Rôle | Port hôte |
|---|---|---|
| `api` | FastAPI (uvicorn, 2 workers, utilisateur non-root) | 8000 |
| `frontend` | build React statique servi par nginx | 3000 → 80 |
| `watcher` | veille réglementaire planifiée (`ingestion.scheduler`) | — |

**Important — URL de l'API dans le frontend :** elle est figée **au build** via l'arg
`REACT_APP_API_URL` (`docker-compose.yml`, service `frontend`). Pour un domaine
public, la changer avant de builder :

```yaml
# docker-compose.yml → frontend.build.args
- REACT_APP_API_URL=https://api.votre-domaine.ma
```

et répercuter cette origine dans `connect-src` de `frontend/nginx.conf` (§5).

---

## 4. HTTPS obligatoire en production

Avec `ENVIRONMENT=production`, le refresh token est posé dans un cookie
`Secure` (transmis uniquement en HTTPS). **Servir l'app en HTTP simple casse la
connexion** (le cookie n'est jamais renvoyé). Deux cas :

- **Test local de la stack de prod** : garder `ENVIRONMENT=development` dans le
  `.env` pour que l'authentification fonctionne sur `http://localhost`.
- **Déploiement réel** : `ENVIRONMENT=production` **derrière un reverse proxy
  HTTPS** (§5).

---

## 5. Reverse proxy HTTPS (déploiement exposé)

Terminer le TLS devant les conteneurs (nginx, Traefik, Caddy…) et router :
`https://lexia.domaine.ma` → `frontend:80`, `https://api.domaine.ma` → `api:8000`.

À aligner ensuite :
- `CORS_ORIGINS` (`.env`) = origine publique du frontend.
- `REACT_APP_API_URL` (build arg) = origine publique de l'API, puis **rebuild** du frontend.
- `connect-src` dans `frontend/nginx.conf` = origine publique de l'API (le CSP par
  défaut n'autorise que `localhost:8000`).

Exemple minimal (Caddy) :

```
lexia.domaine.ma { reverse_proxy frontend:80 }
api.domaine.ma   { reverse_proxy api:8000 }
```

---

## 6. Base de données

- **SQLite** (défaut) : fichier dans le volume `./data`, suffisant pour une
  instance unique. Sauvegarde = copie de `data/lexia.db`.
- **PostgreSQL** (recommandé multi-workers/scalabilité) : ajouter un service
  `db` à `docker-compose.yml` et `DATABASE_URL=postgresql://user:pass@db:5432/lexia`.
  Les tables sont créées au démarrage (`init_db` → `create_all` + micro-migrations).

---

## 7. Initialisation du corpus

Les corpus vectoriels vivent dans le volume `./data/vector_stores`. Deux options :

- **Réutiliser le corpus existant** : monter le `./data` déjà peuplé (6 353 passages
  aujourd'hui) — rien à faire.
- **Reconstruire depuis `data/raw/`** (backend à l'arrêt pour éviter le verrou Chroma) :

```bash
docker compose run --rm api python -m scripts.backfill_corpus
```

Vérifier : `GET /health` doit renvoyer `corpus_ready: true` et `total_chunks > 0`.

---

## 8. Vérification post-déploiement

```bash
curl -f http://localhost:8000/health     # {"status":"ok","corpus_ready":true,...}
```

- Frontend accessible (landing publique + ticker de veille + chat démo).
- Connexion avec un compte, une question renvoie une réponse **sourcée**.
- `docker compose ps` : `api` **healthy**.

---

## 9. Exploitation

```bash
docker compose logs -f api          # logs applicatifs
docker compose restart api          # redémarrage
docker compose down                 # arrêt (les volumes ./data et ./logs persistent)
docker compose up -d --build        # redéploiement après mise à jour du code
```

- **Veille** : le service `watcher` s'exécute selon `WATCH_INTERVAL_HOURS`.
- **Notifications e-mail** (optionnel) : renseigner `SMTP_*` dans `.env` ; sinon
  dégradation silencieuse (les notifications in-app restent actives).

---

## 10. Check-list sécurité avant mise en ligne

- [ ] `SECRET_KEY` généré aléatoirement, jamais commité.
- [ ] `ENVIRONMENT=production`, `DEBUG=false` (docs API désactivées).
- [ ] HTTPS terminé par le reverse proxy ; cookies `Secure` effectifs.
- [ ] `CORS_ORIGINS` limité à l'origine du frontend (pas de `*`).
- [ ] `connect-src` (CSP nginx) pointant sur l'API publique uniquement.
- [ ] Clés LLM/SMTP uniquement dans `.env` (hors Git), volumes `./data`/`./logs` sauvegardés.
- [ ] Rate limiting actif (`RATE_LIMIT_REQUESTS`/`_WINDOW_SECONDS`) — mémoire par
      instance ; derrière plusieurs répliques, prévoir un store partagé (Redis).
