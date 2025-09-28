# backend/services/historico_service.py

from datetime import datetime
from ..models.database import db
from ..models.aluno import Aluno
from ..models.disciplina import Disciplina
from ..models.historico_disciplina import HistoricoDisciplina
from ..models.historico import HistoricoAluno
from sqlalchemy import select, and_
from flask import current_app

class HistoricoService:

    # --- MÉTODOS EXISTENTES (DISCIPLINAS E NOTAS) ---

    @staticmethod
    def get_historico_disciplinas_for_aluno(aluno_id: int):
        """Busca todos os registros de disciplinas (matrículas) para um aluno específico."""
        stmt = select(HistoricoDisciplina).where(HistoricoDisciplina.aluno_id == aluno_id).order_by(HistoricoDisciplina.id)
        return db.session.scalars(stmt).all()

    @staticmethod
    def get_historico_atividades_for_aluno(aluno_id: int):
        """Busca todos os registros de atividades (ex: mudanças de perfil) para um aluno específico."""
        stmt = select(HistoricoAluno).where(HistoricoAluno.aluno_id == aluno_id).order_by(HistoricoAluno.data_inicio.desc())
        return db.session.scalars(stmt).all()

    @staticmethod
    def avaliar_aluno(historico_id: int, form_data: dict):
        """Lança ou atualiza as notas de um aluno em uma disciplina e calcula a média final."""
        registro = db.session.get(HistoricoDisciplina, historico_id)
        if not registro:
            return False, "Registro de matrícula não encontrado.", None

        try:
            nota_p1 = float(form_data.get('nota_p1')) if form_data.get('nota_p1') else None
            nota_p2 = float(form_data.get('nota_p2')) if form_data.get('nota_p2') else None
            nota_rec = float(form_data.get('nota_rec')) if form_data.get('nota_rec') else None

            registro.nota_p1 = nota_p1
            registro.nota_p2 = nota_p2
            registro.nota_rec = nota_rec

            if nota_p1 is not None and nota_p2 is not None:
                mpd = (nota_p1 + nota_p2) / 2
                if mpd < 7.0 and nota_rec is not None:
                    mfd = (nota_p1 + nota_p2 + nota_rec) / 3
                    registro.nota = round(mfd, 3)
                else:
                    registro.nota = round(mpd, 3)
            else:
                registro.nota = None

            db.session.commit()
            return True, "Avaliação salva com sucesso.", registro.aluno_id
        except (ValueError, TypeError):
            db.session.rollback()
            return False, "As notas devem ser números válidos.", registro.aluno_id
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao salvar avaliação: {e}")
            return False, "Ocorreu um erro ao salvar a avaliação.", registro.aluno_id

    # --- NOVOS MÉTODOS (CRUD DE ATIVIDADES) ---

    @staticmethod
    def add_atividade_aluno(aluno_id: int, data: dict):
        """Adiciona um novo registro de atividade ao histórico de um aluno."""
        if not all([aluno_id, data.get('tipo'), data.get('descricao'), data.get('data_inicio')]):
            return False, "Todos os campos (Tipo, Descrição, Data) são obrigatórios."

        try:
            nova_atividade = HistoricoAluno(
                aluno_id=aluno_id,
                tipo=data['tipo'],
                descricao=data['descricao'],
                data_inicio=datetime.fromisoformat(data['data_inicio'])
            )
            db.session.add(nova_atividade)
            db.session.commit()
            return True, "Atividade adicionada ao histórico com sucesso!"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao adicionar atividade: {e}")
            return False, "Ocorreu um erro ao adicionar a atividade."

    @staticmethod
    def update_atividade_aluno(atividade_id: int, data: dict):
        """Atualiza um registro de atividade existente."""
        atividade = db.session.get(HistoricoAluno, atividade_id)
        if not atividade:
            return False, "Registro de atividade não encontrado."

        if not all([data.get('tipo'), data.get('descricao'), data.get('data_inicio')]):
            return False, "Todos os campos (Tipo, Descrição, Data) são obrigatórios."

        try:
            atividade.tipo = data['tipo']
            atividade.descricao = data['descricao']
            atividade.data_inicio = datetime.fromisoformat(data['data_inicio'])
            db.session.commit()
            return True, "Atividade atualizada com sucesso!"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar atividade: {e}")
            return False, "Ocorreu um erro ao atualizar a atividade."

    @staticmethod
    def delete_atividade_aluno(atividade_id: int):
        """Exclui um registro de atividade do histórico."""
        atividade = db.session.get(HistoricoAluno, atividade_id)
        if not atividade:
            return False, "Registro de atividade não encontrado."

        try:
            db.session.delete(atividade)
            db.session.commit()
            return True, "Atividade removida do histórico com sucesso!"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao deletar atividade: {e}")
            return False, "Ocorreu um erro ao remover a atividade."