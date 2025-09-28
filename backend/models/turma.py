from __future__ import annotations
import typing as t
from .database import db
from sqlalchemy.orm import Mapped, mapped_column, relationship

if t.TYPE_CHECKING:
    from .aluno import Aluno
    from .school import School

class Turma(db.Model):
    __tablename__ = 'turmas'

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(100), unique=True, nullable=False) # Ex: "1º Pelotão", "Turma de Formação 2025"
    ano: Mapped[int] = mapped_column(nullable=True)
    school_id: Mapped[int] = mapped_column(db.ForeignKey('schools.id'), nullable=False)

    # Uma turma pode ter vários alunos
    alunos: Mapped[list["Aluno"]] = relationship(back_populates="turma")
    school: Mapped["School"] = relationship(back_populates="turmas")

    def __init__(self, nome: str, ano: t.Optional[int] = None, **kw: t.Any) -> None:
        super().__init__(nome=nome, ano=ano, **kw)

    def __repr__(self):
        return f"<Turma id={self.id} nome='{self.nome}'>"