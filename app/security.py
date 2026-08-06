import hashlib, hmac, os
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"{salt.hex()}:{digest.hex()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split(":", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000).hex()
        return hmac.compare_digest(actual, digest_hex)
    except Exception: return False

def current_user(request: Request, db: Session):
    from .models import User
    uid = request.session.get("user_id")
    if not uid: raise HTTPException(401, "Authentication required")
    user = db.get(User, uid)
    if not user or not user.active: raise HTTPException(401, "Invalid session")
    return user
