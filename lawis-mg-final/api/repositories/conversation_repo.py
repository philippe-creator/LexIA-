from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from core.database import Conversation, Message

class ConversationRepository:
    def __init__(self, db: Session): self.db = db

    def create(self, user_id: str, title: str = None, domain: str = None) -> Conversation:
        conv = Conversation(user_id=user_id, title=title, domain=domain)
        self.db.add(conv); self.db.commit(); self.db.refresh(conv)
        return conv

    def get(self, conv_id: str, user_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user_id).first()

    def list_for_user(self, user_id: str, limit: int = 20, offset: int = 0) -> list:
        return self.db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).offset(offset).limit(limit).all()

    def get_or_create(self, user_id: str, conv_id: Optional[str], query: str) -> Conversation:
        if conv_id:
            conv = self.get(conv_id, user_id)
            if conv:
                conv.updated_at = datetime.now(timezone.utc); self.db.commit()
                return conv
        title = query[:60] + ("..." if len(query) > 60 else "")
        return self.create(user_id=user_id, title=title)

    def add_message(self, conv_id: str, role: str, content: str, citations=None, domains_searched=None, confidence_score=None, retrieval_method=None) -> Message:
        msg = Message(conversation_id=conv_id, role=role, content=content, citations=citations or [], domains_searched=domains_searched or [], confidence_score=confidence_score, retrieval_method=retrieval_method)
        self.db.add(msg); self.db.commit(); self.db.refresh(msg)
        return msg

    def get_history(self, conv_id: str, limit: int = 10) -> list:
        return self.db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at.desc()).limit(limit).all()[::-1]

    def set_feedback(self, message_id: str, user_id: str, feedback: Optional[str]) -> Optional[Message]:
        """Enregistre le retour ("up"/"down"/None) sur une réponse de l'assistant,
        après vérification que le message appartient bien à une conversation de
        l'utilisateur (isolation : on ne peut pas noter le message d'autrui)."""
        msg = (
            self.db.query(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(Message.id == message_id, Conversation.user_id == user_id, Message.role == "assistant")
            .first()
        )
        if not msg:
            return None
        msg.feedback = feedback
        self.db.commit(); self.db.refresh(msg)
        return msg

    def delete(self, conv_id: str, user_id: str) -> bool:
        conv = self.get(conv_id, user_id)
        if not conv: return False
        self.db.delete(conv); self.db.commit()
        return True
