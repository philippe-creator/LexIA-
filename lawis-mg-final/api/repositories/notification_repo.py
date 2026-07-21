from sqlalchemy.orm import Session
from core.database import Notification

class NotificationRepository:
    def __init__(self, db: Session): self.db = db

    def create(self, user_id: str, type: str, title: str, message: str, data: dict = None) -> Notification:
        n = Notification(user_id=user_id, type=type, title=title, message=message, data=data or {})
        self.db.add(n); self.db.commit(); self.db.refresh(n)
        return n

    def list_for_user(self, user_id: str, limit: int = 20, offset: int = 0, unread_only: bool = False) -> tuple[list, int]:
        q = self.db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            q = q.filter(Notification.read == False)
        total = q.count()
        items = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    def mark_read(self, notification_id: str, user_id: str) -> Notification | None:
        n = self.db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
        if not n: return None
        n.read = True; self.db.commit(); self.db.refresh(n)
        return n

    def mark_all_read(self, user_id: str) -> int:
        q = self.db.query(Notification).filter(Notification.user_id == user_id, Notification.read == False)
        count = q.count()
        q.update({"read": True}, synchronize_session=False)
        self.db.commit()
        return count

    def get_unread_count(self, user_id: str) -> int:
        return self.db.query(Notification).filter(Notification.user_id == user_id, Notification.read == False).count()
