# backend/services/disciplina_service.py

from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from flask import current_app
from datetime import date # --- NOVA IMPORTAÇÃO ---

from ..models.database import db
from ..models.disciplina import Disciplina
from ..models.disciplina_turma import DisciplinaTurma
from ..models.historico_disciplina import HistoricoDisciplina
from ..models.aluno import Aluno
from ..models.turma import Turma
from ..models.ciclo import Ciclo
from ..models.horario import Horario
from ..models.semana import Semana # --- NOVA IMPORTAÇÃO ---

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
        Busca todas as disciplinas de uma escola, calcula o progresso de cada uma
        e as agrupa por ciclo.
        """
        disciplinas_query = (
            select(Disciplina)
            .where(Disciplina.school_id == school_id)
            .order_by(Disciplina.ciclo_id, Disciplina.materia)
        )
        disciplinas = db.session.scalars(disciplinas_query).all()
        
        disciplinas_agrupadas = defaultdict(list)
        for disciplina in disciplinas:
            progresso = DisciplinaService.get_dados_progresso(disciplina)
            item = {'disciplina': disciplina, 'progresso': progresso}
            if disciplina.ciclo:
                disciplinas_agrupadas[disciplina.ciclo.nome].append(item)
            
        return dict(sorted(disciplinas_agrupadas.items()))

    # --- FUNÇÃO MODIFICADA PARA CONSIDERAR APENAS AULAS CONCLUÍDAS ---
    @staticmethod
    def get_dados_progresso(disciplina):
        """Calcula as horas agendadas, previstas e o percentual de conclusão de uma disciplina."""
        
        # A consulta agora junta com a tabela de semanas para filtrar pela data
        total_concluido = db.session.scalar(
            select(func.sum(Horario.duracao))
            .join(Semana)
            .where(
                Horario.disciplina_id == disciplina.id,
                Horario.status == 'confirmado',
                Semana.data_fim < date.today() # Apenas aulas de semanas que já terminaram
            )
        ) or 0
        
        carga_horaria = disciplina.carga_horaria_prevista
        
        percentual = 0
        if carga_horaria > 0:
            percentual = round((total_concluido / carga_horaria) * 100)
            
        return {
            'agendado': total_concluido,
            'previsto': carga_horaria,
            'percentual': min(percentual, 100)
        }