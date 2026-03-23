"""
Buat akun API untuk aplikasi yang boleh mengakses RAG chatbot.

Cara pakai:
    python create_user.py mis-app          # buat akun untuk aplikasi MIS
    python create_user.py mobile-app       # buat akun untuk mobile app
    python create_user.py mis-app --reset  # reset password akun yang sudah ada
"""
import sys
import argparse
import secrets
import string
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, engine, Base
import app.models  # noqa
from app.models.user import User
from app.auth import hash_password


def generate_password(length: int = 32) -> str:
    """Generate password acak yang kuat."""
    chars = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(chars) for _ in range(length))


def create_user(username: str, description: str, reset: bool = False):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    existing = db.query(User).filter(User.username == username).first()

    if existing and not reset:
        print(f"[ERROR] Akun '{username}' sudah ada.")
        print(f"        Gunakan --reset untuk generate password baru.")
        db.close()
        sys.exit(1)

    password = generate_password()
    hashed = hash_password(password)

    if existing:
        existing.hashed_password = hashed
        existing.is_active = True
        db.commit()
        action = "Password direset"
    else:
        user = User(username=username, hashed_password=hashed, description=description)
        db.add(user)
        db.commit()
        action = "Akun dibuat"

    db.close()

    print()
    print("=" * 50)
    print(f"  {action}: {username}")
    print("=" * 50)
    print(f"  Username    : {username}")
    print(f"  Password    : {password}")
    print(f"  Deskripsi   : {description}")
    print("=" * 50)
    print()
    print("  SIMPAN PASSWORD INI SEKARANG — tidak bisa dilihat lagi.")
    print()
    print("  Cara pakai di aplikasi MIS:")
    print(f"    POST /api/auth/token")
    print(f"    Body: {{\"username\": \"{username}\", \"password\": \"<password>\"}}")
    print(f"    → Simpan access_token, kirim di setiap request:")
    print(f"    Authorization: Bearer <access_token>")
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Buat akun API untuk RAG Chatbot.')
    parser.add_argument('username', help='Nama akun (contoh: mis-app, mobile-app)')
    parser.add_argument('--description', default='', help='Deskripsi akun')
    parser.add_argument('--reset', action='store_true', help='Reset password akun yang sudah ada')
    args = parser.parse_args()

    desc = args.description or args.username
    create_user(args.username, desc, reset=args.reset)
