# backend/services/instrutor_service.py

from flask import current_app
from sqlalchemy import select, delete, or_
from sqlalchemy.exc import IntegrityError

from backend.models.database import db
from backend.models.instrutor import Instrutor
from backend.models.user import User
from backend.models.user_school import UserSchool
from backend.models.disciplina_turma import DisciplinaTurma
from backend.models.horario import Horario


class InstrutorService:
    @staticmethod
    def _find_user_by_email_or_username(email: str):
        email = (email or '').strip()
        if not email:
            return None
        return db.session.scalar(select(User).where(User.email == email))

    @staticmethod
    def _ensure_user_school(user_id: int, school_id: int, role: str = 'instrutor'):
        if not school_id:
            return
        exists = db.session.query(UserSchool.id).filter_by(user_id=user_id, school_id=school_id).first()
        if not exists:
            db.session.add(UserSchool(user_id=user_id, school_id=school_id, role=role))

    @staticmethod
    def create_full_instrutor(data, school_id):
        """Cria um usuário e o perfil de Instrutor, vinculando-o à escola."""
        try:
            matricula = (data.get('matricula') or '').strip()
            email = (data.get('email') or '').strip()
            password = (data.get('password') or '').strip()
            nome_completo = (data.get('nome_completo') or '').strip()
            nome_de_guerra = (data.get('nome_de_guerra') or '').strip()
            posto_sel = (data.get('posto_graduacao_select') or '').strip()
            posto_outro = (data.get('posto_graduacao_outro') or '').strip()
            posto = posto_outro if (posto_sel == 'Outro' and posto_outro) else (posto_sel or None)
            telefone = (data.get('telefone') or '').strip() or None
            is_rr = str(data.get('is_rr') or '').lower() in ('sim', 'true', '1', 'on')

            if not matricula:
                return False, "O campo Matrícula é obrigatório."
            if not email:
                return False, "O campo E-mail é obrigatório."
            if not password:
                return False, "O campo Senha é obrigatório."

            if db.session.scalar(select(User).where(User.matricula == matricula)):
                return False, f"A Matrícula '{matricula}' já está em uso por outro usuário."
            if db.session.scalar(select(User).where(User.email == email)):
                return False, f"O e-mail '{email}' já está em uso por outro usuário."

            # CRIAÇÃO DO USUÁRIO COM STATUS ATIVO
            user = User(
                email=email,
                username=email,
                role='instrutor',
                nome_completo=nome_completo or None,
                nome_de_guerra=nome_de_guerra or None,
                matricula=matricula,
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            instrutor = Instrutor(
                user_id=user.id,
                posto_graduacao=posto,
                telefone=telefone,
                is_rr=is_rr
            )
            db.session.add(instrutor)

            if school_id:
                InstrutorService._ensure_user_school(user.id, int(school_id), role='instrutor')

            db.session.commit()
            return True, "Instrutor cadastrado com sucesso!"

        except IntegrityError as e:
            db.session.rollback()
            # Log the original exception message if available
            msg = getattr(e, 'orig', e)
            current_app.logger.error("Erro de Integridade Inesperado: %s", msg)
            return False, "Erro de integridade da base de dados. Verifique os dados e tente novamente."

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Erro geral ao criar instrutor")
            return False, "Ocorreu um erro inesperado ao criar o instrutor."

    # --- FUNÇÃO NOVA ADICIONADA AQUI ---
    @staticmethod
    def create_profile_for_user(user_id: int, data: dict):
        """Cria um perfil de Instrutor para um usuário já existente."""
        user = db.session.get(User, user_id)
        if not user:
            return False, "Utilizador não encontrado."
        
        if user.instrutor_profile:
            return False, "Este utilizador já possui um perfil de instrutor."

        try:
            posto_sel = (data.get('posto_graduacao_select') or '').strip()
            posto_outro = (data.get('posto_graduacao_outro') or '').strip()
            posto = posto_outro if (posto_sel == 'Outro' and posto_outro) else (posto_sel or None)
            telefone = (data.get('telefone') or '').strip() or None
            is_rr = str(data.get('is_rr') or '').lower() in ('sim', 'true', '1', 'on')

            # Cria o novo perfil
            new_profile = Instrutor(
                user_id=user_id,
                posto_graduacao=posto,
                telefone=telefone,
                is_rr=is_rr
            )
            db.session.add(new_profile)
            db.session.commit()
            return True, "Perfil de instrutor completado com sucesso."

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Erro ao criar perfil de instrutor para utilizador existente")
            return False, "Ocorreu um erro inesperado ao salvar o perfil."
            
    @staticmethod
    def get_instrutor_by_id(instrutor_id: int):
        return db.session.get(Instrutor, instrutor_id)

    @staticmethod
    def get_all_instrutores():
        stmt = select(Instrutor).join(User).order_by(User.nome_completo)
        return db.session.scalars(stmt).all()

    @staticmethod
    def update_instrutor(instrutor_id: int, data: dict):
        instrutor = db.session.get(Instrutor, instrutor_id)
        if not instrutor:
            return False, "Instrutor não encontrado."
        try:
            nome_completo = (data.get('nome_completo') or '').strip()
            nome_de_guerra = (data.get('nome_de_guerra') or '').strip()
            telefone = (data.get('telefone') or '').strip()

            posto_sel = (data.get('posto_graduacao_select') or '').strip()
            posto_outro = (data.get('posto_graduacao_outro') or '').strip()
            posto = posto_outro if (posto_sel == 'Outro' and posto_outro) else (posto_sel or None)
            
            is_rr = str(data.get('is_rr') or '').lower() in ('sim', 'true', '1', 'on')

            user = db.session.get(User, instrutor.user_id)
            if user:
                if nome_completo:
                    user.nome_completo = nome_completo
                if nome_de_guerra:
                    user.nome_de_guerra = nome_de_guerra

            instrutor.telefone = (telefone or None)
            instrutor.posto_graduacao = posto
            instrutor.is_rr = is_rr

            db.session.commit()
            return True, "Instrutor atualizado com sucesso."
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar instrutor")
            return False, f"Erro ao atualizar instrutor: {str(e)}"

    @staticmethod
    def delete_instrutor(instrutor_id: int):
        instrutor = db.session.get(Instrutor, instrutor_id)
        if not instrutor:
            return False, "Instrutor não encontrado."
        
        try:
            user_a_deletar = instrutor.user
            if user_a_deletar:
                db.session.delete(user_a_deletar)
                db.session.commit()
                return True, "Instrutor e usuário vinculado foram excluídos com sucesso."
            else:
                db.session.delete(instrutor)
                db.session.commit()
                return True, "Perfil de instrutor órfão removido com sucesso."

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao excluir instrutor: {e}")
            return False, f"Erro ao excluir instrutor: {str(e)}"