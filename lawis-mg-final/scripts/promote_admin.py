"""
Promeut un compte existant au rôle "admin". C'est la SEULE façon de créer un
admin : le rôle "admin" est délibérément exclu du schéma d'inscription publique
(/auth/register) — voir api/schemas/auth.py.

Usage (backend arrêté ou non, la base SQLite tolère l'accès concurrent en lecture/écriture ponctuelle) :
    python -m scripts.promote_admin admin@exemple.ma
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
        if user.role == "admin":
            print(f"{user.username} ({email}) est déjà admin.")
            return
        previous_role = user.role
        user.role = "admin"
        db.commit()
        print(f"{user.username} ({email}) promu admin (rôle précédent : {previous_role}).")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage : python -m scripts.promote_admin <email>")
        sys.exit(1)
    promote(sys.argv[1])
