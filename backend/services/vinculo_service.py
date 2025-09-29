# backend/services/vinculo_service.py
from flask import current_app
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload

from ..models.database import db
from ..models.disciplina_turma import DisciplinaTurma
from ..models.turma import Turma
from ..models.instrutor import Instrutor
from ..models.disciplina import Disciplina


class VinculoService:
    @staticmethod
    def get_all_vinculos(turma_filtrada: str = '', disciplina_filtrada_id: int = None):
        # Carrega ambos os instrutores para exibição correta
        query = db.select(DisciplinaTurma).options(
            joinedload(DisciplinaTurma.instrutor_1).joinedload(Instrutor.user),
            joinedload(DisciplinaTurma.instrutor_2).joinedload(Instrutor.user),
            joinedload(DisciplinaTurma.disciplina)
        )

        if turma_filtrada:
            query = query.filter(DisciplinaTurma.pelotao == turma_filtrada)

        if disciplina_filtrada_id:
            query = query.filter(DisciplinaTurma.disciplina_id == disciplina_filtrada_id)

        query = query.order_by(DisciplinaTurma.pelotao, DisciplinaTurma.disciplina_id)
        return db.session.scalars(query).all()

    @staticmethod
    def add_vinculo(instrutor_id: int, turma_id: int, disciplina_id: int):
        if not all([instrutor_id, turma_id, disciplina_id]):
            return False, 'Todos os campos são obrigatórios.'

        turma = db.session.get(Turma, turma_id)
        if not turma:
            return False, 'Turma não encontrada.'

        # Procura por um vínculo para esta turma e disciplina
        vinculo_existente = db.session.scalars(select(DisciplinaTurma).filter_by(
            disciplina_id=disciplina_id,
            pelotao=turma.nome
        )).first()

        try:
            # --- LÓGICA DE CORREÇÃO PARA AMBOS OS CENÁRIOS ---
            if vinculo_existente:
                # Se o vínculo já existe, tenta preencher um slot de instrutor vazio
                if vinculo_existente.instrutor_id_1 is None:
                    vinculo_existente.instrutor_id_1 = instrutor_id
                    message = 'Instrutor vinculado (slot 1) com sucesso!'
                elif vinculo_existente.instrutor_id_2 is None:
                    # Evita vincular o mesmo instrutor duas vezes
                    if vinculo_existente.instrutor_id_1 == instrutor_id:
                        return False, 'Este instrutor já está no slot 1 para esta disciplina.'
                    vinculo_existente.instrutor_id_2 = instrutor_id
                    message = 'Instrutor vinculado (slot 2) com sucesso!'
                else:
                    return False, 'Ambos os slots de instrutor para esta disciplina/turma já estão ocupados.'
            else:
                # Se não existe, cria um novo vínculo com o instrutor no primeiro slot
                novo_vinculo = DisciplinaTurma(
                    instrutor_id_1=instrutor_id,
                    pelotao=turma.nome,
                    disciplina_id=disciplina_id
                )
                db.session.add(novo_vinculo)
                message = 'Vínculo criado com sucesso!'
            
            db.session.commit()
            return True, message
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao adicionar vínculo: {e}")
            return False, f"Erro ao adicionar vínculo: {str(e)}"

    @staticmethod
    def edit_vinculo(vinculo_id: int, instrutor_id: int, turma_id: int, disciplina_id: int):
        vinculo = db.session.get(DisciplinaTurma, vinculo_id)
        if not vinculo:
            return False, 'Vínculo não encontrado.'

        if not all([instrutor_id, turma_id, disciplina_id]):
            return False, 'Todos os campos são obrigatórios.'

        turma = db.session.get(Turma, turma_id)
        if not turma:
            return False, 'Turma não encontrada.'

        try:
            vinculo.instrutor_id_1 = instrutor_id
            vinculo.pelotao = turma.nome
            vinculo.disciplina_id = disciplina_id
            
            db.session.commit()
            return True, 'Vínculo atualizado com sucesso!'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao editar vínculo: {e}")
            return False, f"Erro ao editar vínculo: {str(e)}"

    @staticmethod
    def delete_vinculo(vinculo_id: int):
        vinculo = db.session.get(DisciplinaTurma, vinculo_id)
        if not vinculo:
            return False, 'Vínculo não encontrado.'

        try:
            db.session.delete(vinculo)
            db.session.commit()
            return True, 'Vínculo excluído com sucesso!'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao excluir vínculo: {e}")
            return False, f"Erro ao excluir vínculo: {str(e)}"