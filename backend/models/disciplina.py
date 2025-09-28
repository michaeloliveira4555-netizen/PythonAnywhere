# backend/models/disciplina.py

from __future__ import annotations
import typing as t
from datetime import datetime, timezone
from .database import db
from sqlalchemy.orm import Mapped, mapped_column, relationship

if t.TYPE_CHECKING:
    from .historico_disciplina import HistoricoDisciplina
    from .disciplina_turma import DisciplinaTurma
    from .school import School
    from .ciclo import Ciclo  # Importa o novo modelo

class Disciplina(db.Model):
    __tablename__ = 'disciplinas'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    materia: Mapped[str] = mapped_column(db.String(100), unique=True)
    carga_horaria_prevista: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    school_id: Mapped[int] = mapped_column(db.ForeignKey('schools.id'), nullable=False)
    school: Mapped["School"] = relationship(back_populates="disciplinas")
    
    # ALTERAÇÃO: Substituído o campo de inteiro por uma relação
    ciclo_id: Mapped[int] = mapped_column(db.ForeignKey('ciclos.id'), nullable=False)
    ciclo: Mapped["Ciclo"] = relationship(back_populates="disciplinas")
    
    historico_disciplinas: Mapped[list["HistoricoDisciplina"]] = relationship(back_populates="disciplina")
    associacoes_turmas: Mapped[list["DisciplinaTurma"]] = relationship(back_populates="disciplina")
    
    def __init__(self, materia: str, carga_horaria_prevista: int, school_id: int, ciclo_id: int, **kw: t.Any) -> None:
        super().__init__(materia=materia, carga_horaria_prevista=carga_horaria_prevista, school_id=school_id, ciclo_id=ciclo_id, **kw)

    def __repr__(self):
        ciclo_nome = self.ciclo.nome if self.ciclo else 'N/A'
        return f"<Disciplina id={self.id} materia='{self.materia}' ciclo='{ciclo_nome}'>"