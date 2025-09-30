# backend/services/uniqueness.py
import re
from typing import Optional, Tuple

from sqlalchemy import select

from backend.models.user import User


def norm_email(value: Optional[str]) -> Optional[str]:
    return value.strip().lower() if value else None


def norm_matricula(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    # Remove espaços e caracteres não numéricos por padrão
    normalized = re.sub(r"\D+", "", value.strip())
    return normalized or None


def check_uniqueness(db, email: Optional[str], matricula: Optional[str]) -> Tuple[bool, str]:
    """
    Retorna (ok: bool, detalhe: str). ok=True se não encontrou conflito.
    """
    email_norm = norm_email(email)
    matricula_norm = norm_matricula(matricula)

    if email_norm:
        exists_email = db.session.scalar(select(User).where(User.email == email_norm))
        if exists_email:
            return False, 'E-mail já está em uso na tabela de usuários.'

    if matricula_norm:
        exists_matricula = db.session.scalar(select(User).where(User.matricula == matricula_norm))
        if exists_matricula:
            return False, 'Matrícula já está em uso na tabela de usuários.'

    return True, 'OK'
