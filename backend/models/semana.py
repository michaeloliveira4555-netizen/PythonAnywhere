from __future__ import annotations
import typing as t
from datetime import date
from .database import db
from sqlalchemy.orm import Mapped, mapped_column

class Semana(db.Model):
    __tablename__ = 'semanas'

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(100), nullable=False)
    data_inicio: Mapped[date] = mapped_column(db.Date, nullable=False)
    data_fim: Mapped[date] = mapped_column(db.Date, nullable=False)

    ciclo: Mapped[int] = mapped_column(db.Integer, nullable=False, server_default='1')

    mostrar_periodo_13: Mapped[bool] = mapped_column(default=False, server_default='0')
    mostrar_periodo_14: Mapped[bool] = mapped_column(default=False, server_default='0')
    mostrar_periodo_15: Mapped[bool] = mapped_column(default=False, server_default='0')
    
    mostrar_sabado: Mapped[bool] = mapped_column(default=False, server_default='0')
    periodos_sabado: Mapped[int] = mapped_column(default=0, server_default='0')
    mostrar_domingo: Mapped[bool] = mapped_column(default=False, server_default='0')
    periodos_domingo: Mapped[int] = mapped_column(default=0, server_default='0')

    def __init__(self, nome: str, data_inicio: date, data_fim: date, ciclo: int = 1, **kw: t.Any) -> None:
        super().__init__(nome=nome, data_inicio=data_inicio, data_fim=data_fim, ciclo=ciclo, **kw)

    def __repr__(self):
        return f"<Semana id={self.id} nome='{self.nome}'>"