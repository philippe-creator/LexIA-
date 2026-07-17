from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, create_engine, JSON
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
    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()

def _run_lightweight_migrations():
    """Migrations minimalistes idempotentes pour les colonnes ajoutées après la
    création initiale d'une table (pas d'Alembic sur ce projet). `create_all`
    ne modifie jamais une table existante — on ajoute donc les colonnes
    manquantes à la main. À remplacer par Alembic si le schéma se complexifie."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "messages" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("messages")}
    if "feedback" not in existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE messages ADD COLUMN feedback VARCHAR(4)"))

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("UserDocument", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    def to_dict(self):
        return {"id":self.id,"email":self.email,"username":self.username,"full_name":self.full_name,"role":self.role,"profession":self.profession,"legal_level":self.legal_level,"sector":self.sector,"preferred_language":self.preferred_language,"preferences":self.preferences or {},"is_active":self.is_active,"created_at":self.created_at.isoformat() if self.created_at else None}

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
    # Retour utilisateur sur une réponse de l'assistant : "up" / "down" / None.
    feedback = Column(String(4), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    conversation = relationship("Conversation", back_populates="messages")

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
