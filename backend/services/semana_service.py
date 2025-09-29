# backend/services/semana_service.py

from ..models.database import db
from ..models.semana import Semana
from ..models.horario import Horario
from sqlalchemy import select
from datetime import datetime
from flask import current_app

class SemanaService:
    @staticmethod
    def add_semana(data: dict):
        """Cria uma nova semana a partir dos dados de um formulário."""
        nome = data.get('nome')
        data_inicio = data.get('data_inicio')
        data_fim = data.get('data_fim')
        ciclo_id = data.get('ciclo_id')

        if not all([nome, data_inicio, data_fim, ciclo_id]):
            return False, 'Todos os campos, incluindo o ciclo, são obrigatórios.'

        try:
            nova_semana = Semana(
                nome=nome,
                data_inicio=data_inicio,
                data_fim=data_fim,
                ciclo_id=ciclo_id,
                mostrar_periodo_13=data.get('mostrar_periodo_13', False),
                mostrar_periodo_14=data.get('mostrar_periodo_14', False),
                mostrar_periodo_15=data.get('mostrar_periodo_15', False),
                mostrar_sabado=data.get('mostrar_sabado', False),
                periodos_sabado=data.get('periodos_sabado') or 0,
                mostrar_domingo=data.get('mostrar_domingo', False),
                periodos_domingo=data.get('periodos_domingo') or 0
            )
            db.session.add(nova_semana)
            db.session.commit()
            return True, 'Nova semana cadastrada com sucesso!'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao adicionar semana: {e}")
            return False, f"Erro ao adicionar semana: {str(e)}"
            
    @staticmethod
    def delete_semana(semana_id: int):
        semana = db.session.get(Semana, semana_id)
        if not semana:
            return False, 'Semana não encontrada.'

        try:
            horarios_count = db.session.query(Horario).filter_by(semana_id=semana_id).count()
            if horarios_count > 0:
                return False, f'Não é possível excluir esta semana, pois existem {horarios_count} aulas agendadas nela.'
                
            db.session.delete(semana)
            db.session.commit()
            return True, 'Semana deletada com sucesso.'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao deletar semana: {e}")
            return False, f"Erro ao deletar semana: {str(e)}"