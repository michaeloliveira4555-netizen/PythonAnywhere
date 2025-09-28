# backend/services/turma_service.py

from flask import current_app
from sqlalchemy import select
from ..models.database import db
from ..models.turma import Turma
from ..models.aluno import Aluno
from ..models.disciplina_turma import DisciplinaTurma
from ..models.turma_cargo import TurmaCargo

class TurmaService:
    @staticmethod
    def create_turma(data, school_id):
        """Cria uma nova turma para uma escola específica."""
        nome_turma = data.get('nome')
        ano = data.get('ano')
        alunos_ids = data.get('alunos_ids', [])

        if not all([nome_turma, ano, school_id]):
            return False, 'Nome, Ano e ID da Escola são obrigatórios.'

        if db.session.execute(select(Turma).filter_by(nome=nome_turma, school_id=school_id)).scalar_one_or_none():
            return False, f'Uma turma com o nome "{nome_turma}" já existe nesta escola.'

        try:
            nova_turma = Turma(nome=nome_turma, ano=int(ano), school_id=school_id)
            db.session.add(nova_turma)
            db.session.flush()

            if alunos_ids:
                db.session.query(Aluno).filter(Aluno.id.in_(alunos_ids)).update({"turma_id": nova_turma.id})
            
            db.session.commit()
            return True, "Turma cadastrada com sucesso!"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar turma: {e}")
            return False, f"Erro ao criar turma: {str(e)}"

    @staticmethod
    def update_turma(turma_id, data):
        """Atualiza os dados de uma turma e a lista de seus alunos."""
        turma = db.session.get(Turma, turma_id)
        if not turma:
            return False, "Turma não encontrada."
            
        novo_nome = data.get('nome')
        if db.session.execute(select(Turma).where(Turma.nome == novo_nome, Turma.id != turma_id, Turma.school_id == turma.school_id)).scalar_one_or_none():
            return False, f'Já existe outra turma com o nome "{novo_nome}" nesta escola.'
            
        try:
            turma.nome = novo_nome
            turma.ano = data.get('ano')
            
            alunos_ids_selecionados = data.get('alunos_ids', [])
            
            db.session.query(Aluno).filter(Aluno.turma_id == turma_id).update({"turma_id": None})
            
            if alunos_ids_selecionados:
                db.session.query(Aluno).filter(Aluno.id.in_(alunos_ids_selecionados)).update({"turma_id": turma_id})
                
            db.session.commit()
            return True, "Turma atualizada com sucesso!"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar turma: {e}")
            return False, f"Erro ao atualizar turma: {str(e)}"

    @staticmethod
    def delete_turma(turma_id):
        """Exclui uma turma e todos os seus vínculos associados."""
        turma = db.session.get(Turma, turma_id)
        if not turma:
            return False, 'Turma não encontrada.'

        try:
            nome_turma_excluida = turma.nome
            
            db.session.query(Aluno).filter(Aluno.turma_id == turma_id).update({"turma_id": None})
            
            db.session.query(TurmaCargo).filter_by(turma_id=turma_id).delete()
            db.session.query(DisciplinaTurma).filter_by(pelotao=turma.nome).delete()
            
            db.session.delete(turma)
            db.session.commit()
            return True, f'Turma "{nome_turma_excluida}" e todos os seus vínculos foram excluídos com sucesso!'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao excluir turma: {e}")
            return False, f'Erro ao excluir a turma: {str(e)}'

    @staticmethod
    def get_cargos_da_turma(turma_id, cargos_lista):
        """Busca os cargos de uma turma e garante que todos da lista existam."""
        cargos_db = db.session.scalars(
            select(TurmaCargo).where(TurmaCargo.turma_id == turma_id)
        ).all()
        cargos_atuais = {cargo.cargo_nome: cargo.aluno_id for cargo in cargos_db}

        for cargo in cargos_lista:
            cargos_atuais.setdefault(cargo, None)
        return cargos_atuais

    @staticmethod
    def atualizar_cargos(turma_id, form_data, cargos_lista):
        """Cria ou atualiza os cargos de uma turma com base nos dados do formulário."""
        if not db.session.get(Turma, turma_id):
            return False, 'Turma não encontrada.'
        
        try:
            for cargo_nome in cargos_lista:
                aluno_id = form_data.get(f'cargo_{cargo_nome}')
                aluno_id = int(aluno_id) if aluno_id else None

                cargo = db.session.scalars(
                    select(TurmaCargo).where(TurmaCargo.turma_id == turma_id, TurmaCargo.cargo_nome == cargo_nome)
                ).first()

                if cargo:
                    if aluno_id is None:
                        db.session.delete(cargo)
                    else:
                        cargo.aluno_id = aluno_id
                elif aluno_id:
                    novo_cargo = TurmaCargo(turma_id=turma_id, cargo_nome=cargo_nome, aluno_id=aluno_id)
                    db.session.add(novo_cargo)
            
            db.session.commit()
            return True, 'Cargos da turma atualizados com sucesso!'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao salvar os cargos: {e}")
            return False, 'Erro interno ao salvar os cargos.'