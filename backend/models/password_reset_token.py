# backend/models/password_reset_token.py

from __future__ import annotations
import typing as t
from datetime import datetime, timezone # <-- Importar timezone
from werkzeug.security import generate_password_hash, check_password_hash
from .database import db
from sqlalchemy.orm import Mapped, mapped_column, relationship

if t.TYPE_CHECKING:
    from .user import User

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id'), nullable=False)
    token_hash: Mapped[str] = mapped_column(db.String(256), nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc)) # <-- CORRIGIDO
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[t.Optional[datetime]] = mapped_column(nullable=True)

    attempts: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int] = mapped_column(default=5)
    revoked: Mapped[bool] = mapped_column(default=False)

    created_by_admin_id: Mapped[t.Optional[int]] = mapped_column(db.ForeignKey('users.id'), nullable=True)

    user: Mapped['User'] = relationship('User', foreign_keys=[user_id])
    created_by_admin: Mapped[t.Optional['User']] = relationship('User', foreign_keys=[created_by_admin_id])

    # Helpers
    @staticmethod
    def hash_token(raw_token: str) -> str:
        return generate_password_hash(raw_token)

    def verify_token(self, raw_token: str) -> bool:
        return check_password_hash(self.token_hash, raw_token)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def is_usable(self) -> bool:
        return (not self.revoked) and (self.used_at is None) and (not self.is_expired()) and (self.attempts < self.max_attempts)