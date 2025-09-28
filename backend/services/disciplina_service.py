# backend/services/disciplina_service.py

from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from flask import current_app

from ..models.database import db
from ..models.disciplina import Disciplina
from ..models.disciplina_turma import DisciplinaTurma
from ..models.historico_disciplina import HistoricoDisciplina
from ..models.aluno import Aluno
from ..models.turma import Turma
from ..models.ciclo import Ciclo

class DisciplinaService:
    @staticmethod
    def create_disciplina(data, school_id):
        """Cria uma nova disciplina e a associa a todos os alunos da escola."""
        materia = data.get('materia')
        carga_horaria = data.get('carga_horaria_prevista')
        ciclo_id = data.get('ciclo_id')

        if not materia or not carga_horaria or not ciclo_id:
            return False, 'Matéria, Carga Horária e Ciclo são obrigatórios.'

        if db.session.execute(select(Disciplina).where(Disciplina.materia == materia, Disciplina.school_id == school_id)).scalar_one_or_none():
            return False, f'A disciplina "{materia}" já existe nesta escola.'

        try:
            nova_disciplina = Disciplina(
                materia=materia,
                carga_horaria_prevista=int(carga_horaria),
                ciclo_id=int(ciclo_id),
                school_id=school_id
            )
            db.session.add(nova_disciplina)
            db.session.flush()

            alunos_da_escola = db.session.scalars(
                select(Aluno).join(Turma).where(Turma.school_id == school_id)
            ).all()

            for aluno in alunos_da_escola:
                matricula = HistoricoDisciplina(aluno_id=aluno.id, disciplina_id=nova_disciplina.id)
                db.session.add(matricula)

            db.session.commit()
            return True, 'Disciplina criada e associada aos alunos da escola com sucesso!'
        except (ValueError, TypeError):
            db.session.rollback()
            return False, 'Dados inválidos fornecidos.'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar disciplina: {e}")
            return False, 'Ocorreu um erro interno ao criar a disciplina.'

    @staticmethod
    def update_disciplina(disciplina_id, data):
        """Atualiza uma disciplina existente."""
        disciplina = db.session.get(Disciplina, disciplina_id)
        if not disciplina:
            return False, 'Disciplina não encontrada.'

        try:
            disciplina.materia = data.get('materia', disciplina.materia)
            disciplina.carga_horaria_prevista = int(data.get('carga_horaria_prevista', disciplina.carga_horaria_prevista))
            disciplina.ciclo_id = int(data.get('ciclo_id', disciplina.ciclo_id))
            db.session.commit()
            return True, 'Disciplina atualizada com sucesso!'
        except (ValueError, TypeError):
            db.session.rollback()
            return False, 'Dados inválidos fornecidos.'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar disciplina: {e}")
            return False, 'Ocorreu um erro interno ao atualizar a disciplina.'

    @staticmethod
    def delete_disciplina(disciplina_id):
        """Exclui uma disciplina e todos os seus registros associados."""
        disciplina = db.session.get(Disciplina, disciplina_id)
        if not disciplina:
            return False, 'Disciplina não encontrada.'

        try:
            db.session.query(HistoricoDisciplina).filter_by(disciplina_id=disciplina_id).delete()
            db.session.query(DisciplinaTurma).filter_by(disciplina_id=disciplina_id).delete()
            db.session.delete(disciplina)
            db.session.commit()
            return True, 'Disciplina e todos os seus registros associados foram excluídos com sucesso!'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao excluir disciplina: {e}")
            return False, 'Ocorreu um erro interno ao excluir a disciplina.'

    @staticmethod
    def get_disciplinas_agrupadas_por_ciclo(school_id: int):
        """
        Busca todas as disciplinas de uma escola e as agrupa por ciclo.
        Retorna um dicionário onde as chaves são os nomes dos ciclos.
        """
        disciplinas_query = (
            select(Disciplina)
            .where(Disciplina.school_id == school_id)
            .order_by(Disciplina.ciclo_id, Disciplina.materia)
        )
        disciplinas = db.session.scalars(disciplinas_query).all()
        
        disciplinas_agrupadas = defaultdict(list)
        for disciplina in disciplinas:
            if disciplina.ciclo:
                disciplinas_agrupadas[disciplina.ciclo.nome].append(disciplina)
            
        return dict(sorted(disciplinas_agrupadas.items()))