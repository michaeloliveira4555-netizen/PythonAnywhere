# backend/models/password_reset_request.py

from __future__ import annotations
from datetime import datetime, timezone
import typing as t

from .database import db
from sqlalchemy.orm import Mapped, mapped_column, relationship

if t.TYPE_CHECKING:
    from .user import User


class PasswordResetRequest(db.Model):
    __tablename__ = 'password_reset_requests'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id'), nullable=False)
    admin_id: Mapped[t.Optional[int]] = mapped_column(db.ForeignKey('users.id'), nullable=True)

    status: Mapped[str] = mapped_column(db.String(20), default='pending', nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    processed_at: Mapped[t.Optional[datetime]] = mapped_column(nullable=True)
    processed_by_admin_id: Mapped[t.Optional[int]] = mapped_column(db.ForeignKey('users.id'), nullable=True)

    note: Mapped[t.Optional[str]] = mapped_column(db.String(255), nullable=True)

    user: Mapped['User'] = relationship('User', foreign_keys=[user_id])
    admin: Mapped[t.Optional['User']] = relationship('User', foreign_keys=[admin_id], lazy='joined', backref='password_reset_requests_assigned')
    processed_by_admin: Mapped[t.Optional['User']] = relationship('User', foreign_keys=[processed_by_admin_id], lazy='joined')

    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    def mark_completed(self, admin_id: int) -> None:
        self.status = self.STATUS_COMPLETED
        self.processed_at = datetime.now(timezone.utc)
        self.processed_by_admin_id = admin_id

    def mark_cancelled(self, admin_id: int) -> None:
        self.status = self.STATUS_CANCELLED
        self.processed_at = datetime.now(timezone.utc)
        self.processed_by_admin_id = admin_id
