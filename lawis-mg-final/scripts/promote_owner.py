"""
Accorde le statut de propriétaire à un compte existant (déjà admin ou non).
C'est la SEULE façon de créer un propriétaire : jamais accordé via l'API —
voir require_owner dans api/core/dependencies.py. Un propriétaire peut
promouvoir/rétrograder d'autres comptes au rôle "admin" depuis le tableau
de bord ; un admin normal ne le peut pas.

Usage :
    python -m scripts.promote_owner proprietaire@exemple.ma
"""
import sys
from core.database import SessionLocal, User


def promote(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Aucun compte pour l'email : {email}")
            return
        if user.is_owner:
            print(f"{user.username} ({email}) est déjà propriétaire.")
            return
        user.is_owner = True
        if user.role != "admin":
            user.role = "admin"  # un propriétaire a nécessairement accès admin
        db.commit()
        print(f"{user.username} ({email}) est maintenant propriétaire (et admin).")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage : python -m scripts.promote_owner <email>")
        sys.exit(1)
    promote(sys.argv[1])
