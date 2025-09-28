from ..models.database import db
from ..models.disciplina_turma import DisciplinaTurma
from ..models.turma import Turma
from ..models.instrutor import Instrutor
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from flask import current_app

class VinculoService:
    @staticmethod
    def get_all_vinculos(turma_filtrada: str = '', disciplina_filtrada_id: int = None):
        # CORREÇÃO APLICADA AQUI: Usando o nome correto do relacionamento 'disciplina'
        query = db.select(DisciplinaTurma).options(
            joinedload(DisciplinaTurma.instrutor_1).joinedload(Instrutor.user),
            joinedload(DisciplinaTurma.disciplina)
        ).filter(DisciplinaTurma.instrutor_id_1.isnot(None))


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

        vinculo_existente = db.session.scalars(select(DisciplinaTurma).filter_by(
            disciplina_id=disciplina_id,
            pelotao=turma.nome
        )).first()

        try:
            if vinculo_existente:
                vinculo_existente.instrutor_id_1 = instrutor_id
                message = 'Vínculo atualizado com sucesso, pois já havia uma disciplina nesta turma!'
            else:
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