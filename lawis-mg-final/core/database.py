from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, create_engine, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from core.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def init_db():
    # NB : on n'appelle PAS Alembic par programme ici. Le dossier local `alembic/`
    # (à la racine du projet, sur le sys.path quand uvicorn démarre) masque le
    # package `alembic` installé, ce qui faisait échouer `from alembic import
    # command` au démarrage. create_all crée toutes les tables manquantes à
    # partir des modèles (users, messages, notifications, document_snapshots…)
    # sans jamais toucher aux tables existantes. Alembic reste disponible pour
    # les migrations versionnées manuelles (dossier alembic/ + alembic.ini).
    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()

def _run_lightweight_migrations():
    """Ajoute les colonnes apparues après la création initiale d'une table —
    create_all ne modifie jamais une table existante. Idempotent."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "messages" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("messages")}
        if "feedback" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE messages ADD COLUMN feedback VARCHAR(4)"))
    if "users" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("users")}
        new_cols = {
            "plan": "ALTER TABLE users ADD COLUMN plan VARCHAR(20) DEFAULT 'free'",
            "questions_used": "ALTER TABLE users ADD COLUMN questions_used INTEGER DEFAULT 0",
            "usage_period_start": "ALTER TABLE users ADD COLUMN usage_period_start DATETIME",
        }
        with engine.begin() as conn:
            for name, ddl in new_cols.items():
                if name not in cols:
                    conn.execute(text(ddl))

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(Enum("admin","juriste","avocat","entreprise","etudiant","particulier", name="user_role"), default="particulier")
    profession = Column(String(100), nullable=True)
    legal_level = Column(Enum("debutant","intermediaire","expert", name="legal_level"), default="intermediaire")
    sector = Column(String(100), nullable=True)
    preferred_language = Column(String(10), default="fr")
    preferences = Column(JSON, default=dict)
    # Abonnement (freemium). Le rôle reste le PROFIL métier (adaptation des
    # réponses) ; le plan est l'OFFRE (quota + fonctionnalités). Voir core/plans.py.
    plan = Column(String(20), default="free")
    questions_used = Column(Integer, default=0)
    usage_period_start = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("UserDocument", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    def to_dict(self):
        return {"id":self.id,"email":self.email,"username":self.username,"full_name":self.full_name,"role":self.role,"profession":self.profession,"legal_level":self.legal_level,"sector":self.sector,"preferred_language":self.preferred_language,"preferences":self.preferences or {},"plan":self.plan or "free","is_active":self.is_active,"created_at":self.created_at.isoformat() if self.created_at else None}

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)
    user = relationship("User", back_populates="refresh_tokens")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=True)
    domain = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    __table_args__ = (Index('ix_conversations_user_id', 'user_id'), Index('ix_conversations_updated_at', 'updated_at'))

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum("user","assistant", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=list)
    domains_searched = Column(JSON, default=list)
    confidence_score = Column(Float, nullable=True)
    retrieval_method = Column(String(50), nullable=True)
    feedback = Column(String(4), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    conversation = relationship("Conversation", back_populates="messages")
    __table_args__ = (Index('ix_messages_conversation_id', 'conversation_id'), Index('ix_messages_created_at', 'created_at'))

class UserDocument(Base):
    __tablename__ = "user_documents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    domain = Column(String(50), nullable=True)
    status = Column(Enum("pending","processing","indexed","error", name="doc_status"), default="pending")
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    checksum = Column(String(64), nullable=True)
    indexed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="documents")
    __table_args__ = (Index('ix_user_documents_user_id', 'user_id'), Index('ix_user_documents_created_at', 'created_at'))

class DocumentSnapshot(Base):
    """Copie du texte intégral d'un document au moment de son ingestion —
    permet de comparer deux versions d'un même texte (BF-17), indépendamment
    des chunks (découpés, donc impropres au diff) stockés dans Chroma."""
    __tablename__ = "document_snapshots"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    domain = Column(String(50), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    source = Column(String(50), nullable=True)
    content_hash = Column(String(64), nullable=False, unique=True)
    full_text = Column(Text, nullable=False)
    char_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index('ix_audit_logs_user_id', 'user_id'), Index('ix_audit_logs_created_at', 'created_at'), Index('ix_audit_logs_action', 'action'))

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, default=dict)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="notifications")
    __table_args__ = (Index('ix_notifications_user_id', 'user_id'), Index('ix_notifications_created_at', 'created_at'), Index('ix_notifications_read', 'read'))
