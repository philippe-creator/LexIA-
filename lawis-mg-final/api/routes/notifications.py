from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from api.core.dependencies import CurrentUser
from api.repositories.notification_repo import NotificationRepository

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/")
async def list_notifications(current_user: CurrentUser, limit: int = 20, offset: int = 0, unread_only: bool = False, db: Session = Depends(get_db)):
    items, total = NotificationRepository(db).list_for_user(current_user.id, limit=limit, offset=offset, unread_only=unread_only)
    return {
        "items": [{"id":n.id,"type":n.type,"title":n.title,"message":n.message,"data":n.data or {},"read":n.read,"created_at":n.created_at.isoformat()} for n in items],
        "total": total, "limit": limit, "offset": offset
    }

@router.get("/unread-count")
async def unread_count(current_user: CurrentUser, db: Session = Depends(get_db)):
    count = NotificationRepository(db).get_unread_count(current_user.id)
    return {"count": count}

@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    n = NotificationRepository(db).mark_read(notification_id, current_user.id)
    if not n: raise HTTPException(404, "Notification introuvable.")
    return {"id": n.id, "read": n.read}

@router.post("/read-all")
async def mark_all_read(current_user: CurrentUser, db: Session = Depends(get_db)):
    count = NotificationRepository(db).mark_all_read(current_user.id)
    return {"marked_read": count}
