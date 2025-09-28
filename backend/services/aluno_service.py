# backend/services/aluno_service.py

import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
from ..models.database import db
from ..models.aluno import Aluno
from ..models.user import User
from ..models.historico import HistoricoAluno
from ..models.turma import Turma
from ..models.disciplina import Disciplina
from ..models.historico_disciplina import HistoricoDisciplina
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from utils.image_utils import allowed_file

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def _save_profile_picture(file):
    if file:
        file.stream.seek(0)
        if allowed_file(file.filename, file.stream, ALLOWED_EXTENSIONS):
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4()}.{ext}"

            upload_folder = os.path.join(current_app.static_folder, 'uploads', 'profile_pics')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)

            return unique_filename
    return None

class AlunoService:
    @staticmethod
    def save_aluno(user_id, data, foto_perfil=None):
        existing_aluno = db.session.execute(
            select(Aluno).where(Aluno.user_id == user_id)
        ).scalar_one_or_none()
        if existing_aluno:
            return False, "Este usuário já possui um perfil de aluno cadastrado."

        user = db.session.get(User, user_id)
        if not user:
            return False, "Usuário não encontrado."
        matricula = user.matricula # Pega a matrícula do usuário

        opm = data.get('opm')
        turma_id = data.get('turma_id')
        if turma_id == 0:
            turma_id = None
        funcao_atual = data.get('funcao_atual')

        if not all([opm]): # Matrícula já vem do usuário
            return False, "O campo OPM é obrigatório."

        try:
            foto_filename = _save_profile_picture(foto_perfil)

            # CORREÇÃO: Removido o argumento 'matricula' que já não existe no modelo Aluno
            novo_aluno = Aluno(
                user_id=user_id,
                opm=opm,
                turma_id=int(turma_id) if turma_id else None,
                funcao_atual=funcao_atual,
                foto_perfil=foto_filename if foto_filename else 'default.png'
            )
            db.session.add(novo_aluno)
            db.session.commit()

            if turma_id:
                turma = db.session.get(Turma, turma_id)
                if turma and turma.school:
                    disciplinas_da_escola = turma.school.disciplinas
                    for disciplina in disciplinas_da_escola:
                        matricula_existente = db.session.execute(
                            select(HistoricoDisciplina).where(
                                HistoricoDisciplina.aluno_id == novo_aluno.id,
                                HistoricoDisciplina.disciplina_id == disciplina.id
                            )
                        ).scalar_one_or_none()
                        if not matricula_existente:
                            nova_matricula = HistoricoDisciplina(aluno_id=novo_aluno.id, disciplina_id=disciplina.id)
                            db.session.add(nova_matricula)

            db.session.commit()
            return True, "Perfil de aluno cadastrado e matriculado nas disciplinas da escola!"
        except IntegrityError:
            db.session.rollback()
            return False, "Erro de integridade dos dados."
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro inesperado ao cadastrar aluno: {e}")
            return False, f"Erro ao cadastrar aluno: {str(e)}"

    @staticmethod
    def get_all_alunos(user, nome_turma=None):
        stmt = select(Aluno).join(User).join(Turma)

        if user.role not in ['super_admin', 'programador']:
            user_school_ids = [us.school_id for us in user.user_schools]
            if not user_school_ids:
                return []
            stmt = stmt.where(Turma.school_id.in_(user_school_ids))
        else:
            stmt = stmt.where(User.role != 'super_admin')

        if nome_turma:
            stmt = stmt.where(Turma.nome == nome_turma)

        stmt = stmt.order_by(User.username)

        return db.session.scalars(stmt).all()

    @staticmethod
    def get_aluno_by_id(aluno_id: int):
        return db.session.get(Aluno, aluno_id)

    @staticmethod
    def update_aluno(aluno_id: int, data: dict, foto_perfil=None):
        aluno = db.session.get(Aluno, aluno_id)
        if not aluno:
            return False, "Aluno não encontrado."

        nome_completo = data.get('nome_completo')
        # A matrícula é atualizada no objeto User, não no Aluno
        matricula_nova = data.get('matricula')
        opm = data.get('opm')
        turma_id_val = data.get('turma_id')
        if turma_id_val == 0:
            turma_id_val = None
        nova_funcao_atual = data.get('funcao_atual')

        if not all([nome_completo, matricula_nova, opm]) or turma_id_val in (None, ''):
            return False, "Nome, Matrícula, OPM e Turma são campos obrigatórios."

        try:
            try:
                nova_turma_id = int(turma_id_val) if turma_id_val not in (None, '') else None
            except (ValueError, TypeError):
                nova_turma_id = None

            alteracoes = []
            if aluno.user:
                if aluno.user.nome_completo != nome_completo:
                    alteracoes.append(f"Nome alterado de '{aluno.user.nome_completo or 'N/A'}' para '{nome_completo or 'N/A'}'")
                if aluno.user.matricula != matricula_nova:
                    alteracoes.append(f"Matrícula alterada de '{aluno.user.matricula or 'N/A'}' para '{matricula_nova or 'N/A'}'")
            if aluno.opm != opm:
                alteracoes.append(f"OPM alterada de '{aluno.opm or 'N/A'}' para '{opm or 'N/A'}'")
            if aluno.turma_id != nova_turma_id:
                turma_antiga = db.session.get(Turma, aluno.turma_id) if aluno.turma_id else None
                nova_turma = db.session.get(Turma, nova_turma_id) if nova_turma_id else None
                alteracoes.append(f"Turma alterada de '{turma_antiga.nome if turma_antiga else 'N/A'}' para '{nova_turma.nome if nova_turma else 'N/A'}'")
            
            old_funcao = aluno.funcao_atual or ''
            new_funcao = nova_funcao_atual or ''
            if old_funcao != new_funcao:
                alteracoes.append(f"Função alterada de '{old_funcao or 'N/A'}' para '{new_funcao or 'N/A'}'")

            if alteracoes:
                log_historico = HistoricoAluno(
                    aluno_id=aluno.id,
                    tipo="Perfil Atualizado",
                    descricao="; ".join(alteracoes),
                    data_inicio=datetime.utcnow()
                )
                db.session.add(log_historico)

            if aluno.user:
                aluno.user.nome_completo = nome_completo
                aluno.user.matricula = matricula_nova
            aluno.opm = opm
            aluno.turma_id = nova_turma_id
            aluno.funcao_atual = nova_funcao_atual

            if foto_perfil and hasattr(foto_perfil, 'filename') and foto_perfil.filename != '':
                foto_filename = _save_profile_picture(foto_perfil)
                if foto_filename:
                    aluno.foto_perfil = foto_filename

            db.session.commit()
            return True, "Perfil do aluno atualizado com sucesso!"

        except IntegrityError:
            db.session.rollback()
            return False, "Erro de integridade dos dados. Verifique se a matrícula já está em uso."
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro inesperado ao atualizar aluno: {e}")
            return False, f"Ocorreu um erro inesperado ao atualizar o perfil. Detalhes: {str(e)}"

    @staticmethod
    def delete_aluno(aluno_id: int):
        aluno = db.session.get(Aluno, aluno_id)
        if not aluno:
            return False, "Aluno não encontrado."

        try:
            user_a_deletar = aluno.user
            if user_a_deletar:
                db.session.delete(user_a_deletar)
                db.session.commit()
                return True, "Aluno e todos os seus registos foram excluídos com sucesso!"
            else:
                db.session.delete(aluno)
                db.session.commit()
                return True, "Perfil de aluno órfão removido com sucesso."

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao excluir aluno: {e}")
            return False, f"Erro ao excluir aluno: {str(e)}"