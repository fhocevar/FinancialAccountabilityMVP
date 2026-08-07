import hashlib
import hmac
import os
from typing import Iterable

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from .models import User


VALID_ROLES = {
    "ADMIN",
    "MANAGER",
    "ADVISOR",
    "REVIEWER",
    "AUDITOR",
}


def hash_password(password: str) -> str:
    salt = os.urandom(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120_000,
    )

    return f"{salt.hex()}:{password_hash.hex()}"


def verify_password(
    password: str,
    stored_hash: str,
) -> bool:
    try:
        salt_hex, expected_hash_hex = stored_hash.split(":", 1)

        salt = bytes.fromhex(salt_hex)

        calculated_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            120_000,
        )

        return hmac.compare_digest(
            calculated_hash.hex(),
            expected_hash_hex,
        )

    except (ValueError, TypeError):
        return False


def current_user(
    request: Request,
    db: Session,
) -> User:
    """
    Retorna o usuário autenticado.

    Levanta 401 caso não exista uma sessão válida.
    """
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user = db.get(User, user_id)

    if not user:
        request.session.clear()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    if not user.active:
        request.session.clear()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    return user


def require_roles(
    request: Request,
    db: Session,
    *allowed_roles: str,
) -> User:
    """
    Valida autenticação e autorização por role.

    ADMIN sempre possui acesso.
    """
    user = current_user(request, db)

    role = (user.role or "").upper()

    if role == "ADMIN":
        return user

    normalized_roles = {
        item.upper()
        for item in allowed_roles
    }

    if role not in normalized_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Access denied. "
                f"Required role: {', '.join(sorted(normalized_roles))}"
            ),
        )

    return user


def require_any_role(
    request: Request,
    db: Session,
    roles: Iterable[str],
) -> User:
    return require_roles(
        request,
        db,
        *roles,
    )