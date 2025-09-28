from ..models.database import db
from ..models.semana import Semana
from sqlalchemy import select
from datetime import datetime, timedelta
import re
from flask import current_app

class SemanaService:
    @staticmethod
    def get_all_semanas():
        return db.session.scalars(select(Semana).order_by(Semana.data_inicio.desc())).all()

    @staticmethod
    def get_semana_by_id(semana_id: int):
        return db.session.get(Semana, semana_id)

    @staticmethod
    def add_semana(nome: str, data_inicio_str: str, data_fim_str: str):
        if not all([nome, data_inicio_str, data_fim_str]):
            return False, 'Todos os campos são obrigatórios.'

        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            return False, 'Formato de data inválido. Use AAAA-MM-DD.'

        try:
            nova_semana = Semana(nome=nome, data_inicio=data_inicio, data_fim=data_fim)
            db.session.add(nova_semana)
            return True, 'Nova semana cadastrada com sucesso!'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao adicionar semana: {e}")
            return False, f"Erro ao adicionar semana: {str(e)}"

    @staticmethod
    def add_proxima_semana():
        ultima_semana = db.session.scalars(select(Semana).order_by(Semana.data_fim.desc())).first()

        if not ultima_semana:
            return False, 'Para adicionar a "próxima semana", você precisa cadastrar a primeira semana manualmente.'

        numeros = re.findall(r'\d+', ultima_semana.nome)
        proximo_numero = int(numeros[-1]) + 1 if numeros else 1
        novo_nome = f"Semana {proximo_numero}"

        dias_para_proxima_segunda = (7 - ultima_semana.data_fim.weekday()) % 7
        nova_data_inicio = ultima_semana.data_fim + timedelta(days=dias_para_proxima_segunda)
        nova_data_fim = nova_data_inicio + timedelta(days=4) # De segunda a sexta

        try:
            nova_semana = Semana(nome=novo_nome, data_inicio=nova_data_inicio, data_fim=nova_data_fim)
            db.session.add(nova_semana)
            return True, f'"{novo_nome}" adicionada com sucesso!'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao adicionar próxima semana: {e}")
            return False, f"Erro ao adicionar próxima semana: {str(e)}"

    @staticmethod
    def update_semana(semana_id: int, nome: str, data_inicio_str: str, data_fim_str: str):
        semana = db.session.get(Semana, semana_id)
        if not semana:
            return False, 'Semana não encontrada.'

        if not all([nome, data_inicio_str, data_fim_str]):
            return False, 'Todos os campos são obrigatórios.'

        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            return False, 'Formato de data inválido. Use AAAA-MM-DD.'

        try:
            semana.nome = nome
            semana.data_inicio = data_inicio
            semana.data_fim = data_fim
            return True, 'Semana atualizada com sucesso!'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar semana: {e}")
            return False, f"Erro ao atualizar semana: {str(e)}"

    @staticmethod
    def delete_semana(semana_id: int):
        semana = db.session.get(Semana, semana_id)
        if not semana:
            return False, 'Semana não encontrada.'

        try:
            db.session.delete(semana)
            return True, 'Semana deletada com sucesso.'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao deletar semana: {e}")
            return False, f"Erro ao deletar semana: {str(e)}"
