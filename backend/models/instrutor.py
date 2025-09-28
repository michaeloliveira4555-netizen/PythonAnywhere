# backend/models/instrutor.py

from __future__ import annotations
import typing as t
from datetime import datetime, timezone
from .database import db
from sqlalchemy.orm import Mapped, mapped_column, relationship

if t.TYPE_CHECKING:
    from .user import User

class Instrutor(db.Model):
    __tablename__ = 'instrutores'

    id: Mapped[int] = mapped_column(primary_key=True)
    # REMOVIDO: A matrícula agora está na tabela User
    # matricula: Mapped[str] = mapped_column(db.String(14), unique=True)
    especializacao: Mapped[str] = mapped_column(db.String(100), nullable=False)
    formacao: Mapped[str] = mapped_column(db.String(100))
    posto_graduacao: Mapped[t.Optional[str]] = mapped_column(db.String(50))
    telefone: Mapped[t.Optional[str]] = mapped_column(db.String(15))
    credor: Mapped[t.Optional[str]] = mapped_column(db.String(100))
    is_rr: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id'), unique=True)
    user: Mapped["User"] = relationship(back_populates="instrutor_profile")

    def __init__(self, user_id: int, especializacao: str, formacao: str,
                 posto_graduacao: t.Optional[str] = None, telefone: t.Optional[str] = None,
                 credor: t.Optional[str] = None, is_rr: bool = False, **kw: t.Any) -> None:
        super().__init__(user_id=user_id, especializacao=especializacao, formacao=formacao,
                         posto_graduacao=posto_graduacao, telefone=telefone, credor=credor, is_rr=is_rr, **kw)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'nome': self.user.username if self.user else None,
            'matricula': self.user.matricula if self.user else None,
            'especialidade': self.especializacao,
            'formacao': self.formacao,
            'posto_graduacao': self.posto_graduacao,
            'telefone': self.telefone,
            'credor': self.credor,
            'is_rr': self.is_rr
        }

    def __repr__(self):
        matricula_repr = self.user.matricula if self.user else 'N/A'
        return f"<Instrutor id={self.id} matricula='{matricula_repr}'>"