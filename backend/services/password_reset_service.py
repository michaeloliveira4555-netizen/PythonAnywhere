import os
import secrets
from datetime import datetime, timedelta, timezone # <-- Importar timezone
from flask import current_app
from ..models.database import db
from ..models.user import User
from ..models.password_reset_token import PasswordResetToken

class PasswordResetService:
    DEFAULT_EXP_MINUTES = 30

    @staticmethod
    def generate_token_for_user(user_id: int, admin_id: int | None = None, exp_minutes: int | None = None) -> str:
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("Usuário não encontrado.")

        minutes = exp_minutes or int(os.environ.get('PASSWORD_RESET_TOKEN_EXP_MIN', PasswordResetService.DEFAULT_EXP_MINUTES))
        raw = PasswordResetService._random_token()
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=PasswordResetToken.hash_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes), # <-- CORRIGIDO
            created_by_admin_id=admin_id
        )
        db.session.add(token)
        db.session.commit()
        return raw

    @staticmethod
    def consume_with_user_and_raw_token(id_func: str, raw_token: str) -> User | None:
        user = db.session.execute(db.select(User).filter_by(id_func=id_func)).scalar_one_or_none()
        if not user:
            return None
        # Busca tokens usáveis mais recentes primeiro
        token = db.session.execute(
            db.select(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id)
            .order_by(PasswordResetToken.created_at.desc())
        ).scalars().first()

        if not token:
            return None

        # Verifica condições de uso
        if not token.is_usable():
            return None

        # Verifica hash do token
        if not token.verify_token(raw_token):
            token.attempts += 1
            db.session.commit()
            return None

        # Marca como usado
        token.used_at = datetime.now(timezone.utc) # <-- CORRIGIDO
        db.session.commit()
        return user

    @staticmethod
    def _random_token(length: int = 12) -> str:
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'  # sem chars ambíguos
        return ''.join(secrets.choice(alphabet) for _ in range(length))
