from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")
    APP_NAME: str = "LexIA Maroc"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000"
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]
    SECRET_KEY: str = "CHANGE_ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 45
    # Plus généreux qu'un reset de mot de passe : un utilisateur peut mettre
    # un moment à consulter son email juste après l'inscription.
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h
    BCRYPT_ROUNDS: int = 12
    # Connexion "Se connecter avec Google" (Google Identity Services, flux
    # ID-token — pas d'échange côté serveur, donc pas besoin du client secret ici).
    GOOGLE_CLIENT_ID: str = ""
    # OCR des PDF scannés via Google Cloud Vision (plus rapide/précis que le
    # Tesseract local). Optionnel : si vide, l'app utilise Tesseract comme
    # avant — et bascule automatiquement dessus si Vision échoue en cours de
    # route (quota épuisé, clé désactivée...), voir ingestion/ocr/pdf_extractor.py.
    GOOGLE_VISION_API_KEY: str = ""
    # Base publique du frontend — sert à construire le lien de réinitialisation
    # de mot de passe envoyé par email ({FRONTEND_URL}/reset-password?token=...).
    FRONTEND_URL: str = "http://localhost:3000"
    # Envoi d'email (vérification de compte, mot de passe oublié, notifications
    # de veille) — via services/notifications/email.send_email(). Deux chemins :
    # BREVO_API_KEY (API HTTP, port 443, prioritaire) ou SMTP_HOST (relais SMTP
    # classique, en repli). Si aucun des deux n'est configuré, send_email()
    # échoue silencieusement (log un avertissement) plutôt que de planter.
    BREVO_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True
    DATABASE_URL: str = "sqlite:///./data/lexia.db"
    LLM_PROVIDER: str = "groq"  # openai | gemini | openrouter | groq
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_MODELS: str = "openai/gpt-oss-120b"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"
    # Modèles de secours (liste séparée par virgules), essayés dans l'ordre si le
    # modèle principal renvoie une erreur récupérable (429/402/timeout/5xx).
    # Vide → aucun fallback (seul OPENROUTER_MODEL est utilisé).
    OPENROUTER_MODELS: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MODELS: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_MODELS: str = ""
    @staticmethod
    def _model_list(primary: str, extra: str) -> list[str]:
        models = [primary] + [m.strip() for m in extra.split(",") if m.strip()]
        seen, out = set(), []
        for m in models:
            if m and m not in seen:
                seen.add(m); out.append(m)
        return out
    @property
    def openrouter_models_list(self) -> list[str]:
        return self._model_list(self.OPENROUTER_MODEL, self.OPENROUTER_MODELS)
    @property
    def openai_models_list(self) -> list[str]:
        return self._model_list(self.OPENAI_MODEL, self.OPENAI_MODELS)
    @property
    def gemini_models_list(self) -> list[str]:
        return self._model_list(self.GEMINI_MODEL, self.GEMINI_MODELS)
    @property
    def groq_models_list(self) -> list[str]:
        return self._model_list(self.GROQ_MODEL, self.GROQ_MODELS)
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048
    MAX_CONTEXT_TOKENS: int = 6000
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # Chemins vers les binaires poppler (pdftoppm...) et tesseract, requis pour
    # l'OCR des PDF scannés. Vides par défaut : sur Linux/Docker, poppler-utils
    # et tesseract-ocr sont installés au niveau système (Dockerfile.api) et déjà
    # sur le PATH — ces réglages ne servent qu'aux postes Windows où ces
    # binaires ne sont pas globalement enregistrés dans le PATH du processus Python.
    POPPLER_PATH: str = ""
    TESSERACT_CMD: str = ""
    # Dossier des modèles de langue (*.traineddata) si différent de celui
    # embarqué avec l'exécutable Tesseract — utile sur ce poste où fra/ara ont
    # été installés dans un dossier accessible en écriture sans droits admin,
    # au lieu de tessdata/ sous Program Files (protégé).
    TESSDATA_PREFIX: str = ""
    VECTOR_STORE_PROVIDER: str = "chroma"
    CHROMA_PERSIST_DIR: str = "./data/vector_stores"
    RAW_DATA_DIR: str = "./data/raw"
    PROCESSED_DATA_DIR: str = "./data/processed"
    UPLOADS_DIR: str = "./data/uploads"
    LOGS_DIR: str = "./logs"
    TOP_K_RETRIEVAL: int = 5
    TOP_K_RERANK: int = 3
    HYBRID_ALPHA: float = 0.7
    QUERY_EXPANSION_ENABLED: bool = True
    # Délai max par variante de recherche. L'embedding multilingual-e5-large est
    # lent sur CPU : au premier appel (modèle froid) ou sous charge, 15 s étaient
    # trop courts — toutes les variantes expiraient et la recherche renvoyait
    # « aucun résultat » à tort. 60 s laisse le temps au chargement/à la charge.
    RETRIEVAL_TIMEOUT_SECONDS: int = 60
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    # Limite dédiée, plus stricte, sur les routes d'authentification — la limite
    # globale (60/60s) laisse passer bien trop de tentatives de mot de passe.
    AUTH_RATE_LIMIT_REQUESTS: int = 10
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 300
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = ["pdf", "docx", "doc", "txt"]
    WATCH_INTERVAL_HOURS: int = 24
    SGG_BASE_URL: str = "https://www.sgg.gov.ma/BO.aspx"
    CNDP_BASE_URL: str = "https://www.cndp.ma"
    DGI_BASE_URL: str = "https://www.tax.gov.ma"
    CNSS_BASE_URL: str = "https://www.cnss.ma"
    OMPIC_BASE_URL: str = "https://www.ompic.ma"
    CSPJ_BASE_URL: str = "https://juriscassation.cspj.ma"
    OPENDATA_API_URL: str = "https://www.data.gov.ma/api/3"
    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
