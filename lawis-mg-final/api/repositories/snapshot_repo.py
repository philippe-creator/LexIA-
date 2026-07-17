import hashlib
from sqlalchemy import desc
from sqlalchemy.orm import Session
from core.database import DocumentSnapshot


def save_snapshot(db: Session, domain: str, filename: str, source: str, full_text: str) -> DocumentSnapshot | None:
    """Enregistre une version du texte intégral d'un document si son contenu
    n'a encore jamais été vu (déduplication par hash) — chaque ingestion d'un
    texte réellement modifié crée une nouvelle version comparable."""
    if not full_text or not full_text.strip():
        return None
    content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    existing = db.query(DocumentSnapshot).filter(DocumentSnapshot.content_hash == content_hash).first()
    if existing:
        return existing
    snap = DocumentSnapshot(domain=domain, filename=filename, source=source, content_hash=content_hash, full_text=full_text, char_count=len(full_text))
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def list_snapshots(db: Session, domain: str) -> list[DocumentSnapshot]:
    return db.query(DocumentSnapshot).filter(DocumentSnapshot.domain == domain).order_by(desc(DocumentSnapshot.created_at)).all()


def get_snapshot(db: Session, snapshot_id: str) -> DocumentSnapshot | None:
    return db.query(DocumentSnapshot).filter(DocumentSnapshot.id == snapshot_id).first()


def list_recent(db: Session, limit: int = 8) -> list[DocumentSnapshot]:
    """Derniers textes intégrés, tous domaines confondus (pour le fil d'actualité
    de la page d'accueil — reflète les ajouts réels au corpus)."""
    return db.query(DocumentSnapshot).order_by(desc(DocumentSnapshot.created_at)).limit(limit).all()
