from sqlalchemy.orm import Session
from api.repositories.notification_repo import NotificationRepository
from services.notifications.email import send_email as send_email_message
from loguru import logger

NOTIFICATION_TYPES = {
    "watch_new_document": "Nouveau document juridique",
    "watch_cycle_completed": "Cycle de veille terminé",
    "document_indexed": "Document indexé",
    "audit_completed": "Audit de contrat terminé",
    "system": "Système",
}

def create_notification(db: Session, user_id: str, type: str, title: str, message: str, data: dict = None, send_email: bool = False) -> dict:
    repo = NotificationRepository(db)
    n = repo.create(user_id=user_id, type=type, title=title, message=message, data=data or {})
    if send_email:
        from core.database import User
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.email:
            subject = f"[LexIA Maroc] {title}"
            html = f"<p>{message}</p>"
            # Fonction renommée à l'import (send_email_message) pour ne pas être
            # masquée par le paramètre booléen send_email de cette fonction.
            send_email_message(user.email, subject, html)
    return {"id": n.id, "type": n.type, "title": n.title, "message": n.message, "read": n.read, "created_at": n.created_at.isoformat()}
