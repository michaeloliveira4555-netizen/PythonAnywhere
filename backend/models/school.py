# backend/models/school.py

from __future__ import annotations
import typing as t
from datetime import datetime, timezone
from .database import db
from sqlalchemy.orm import Mapped, mapped_column, relationship

if t.TYPE_CHECKING:
    from .user import User
    from .user_school import UserSchool
    from .turma import Turma
    from .disciplina import Disciplina

class School(db.Model):
    __tablename__ = 'schools'

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(150), nullable=False)
    slug: Mapped[t.Optional[str]] = mapped_column(db.String(150), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    # RELACIONAMENTOS CORRIGIDOS
    user_schools: Mapped[list['UserSchool']] = relationship('UserSchool', back_populates='school', cascade="all, delete-orphan")
    users: Mapped[list['User']] = relationship('User', secondary='user_schools', back_populates='schools', overlaps="user_schools")
    
    turmas: Mapped[list['Turma']] = relationship(back_populates='school', cascade="all, delete-orphan")
    disciplinas: Mapped[list['Disciplina']] = relationship(back_populates='school', cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<School id={self.id} nome='{self.nome}'>"