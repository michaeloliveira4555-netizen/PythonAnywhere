
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
        u = db.session.scalar(select(User).where(User.email == email))
        if u:
            return u
        return db.session.scalar(select(User).where(User.username == email))

    @staticmethod
    def _ensure_user_school(user_id: int, school_id: int, role: str = 'instrutor'):
        if not school_id:
            return
        exists = db.session.query(UserSchool.id).filter_by(user_id=user_id, school_id=school_id).first()
        if not exists:
            db.session.add(UserSchool(user_id=user_id, school_id=school_id, role=role))

    @staticmethod
    def create_full_instrutor(data, school_id):
        """Cria (ou reaproveita) um usuário e o perfil Instrutor, vinculando à escola.
        - Se já existir User com o mesmo e-mail/username, NÃO exige senha e NÃO altera a senha.
        - Só exige senha quando for criar um novo User.
        - Impede duplicidade por matrícula (se informada) e por e-mail quando já houver perfil de instrutor.
        """
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

            if not email:
                return False, "E-mail é obrigatório."

            # Evitar duplicidade de matrícula no perfil
            if matricula:
                exists_mat = db.session.scalar(select(Instrutor).where(Instrutor.matricula == matricula))
                if exists_mat:
                    return False, "Já existe um instrutor com esta matrícula."

            # Upsert de usuário por e-mail
            user = InstrutorService._find_user_by_email_or_username(email)
            if user:
                # Se já tinha perfil de instrutor, impedir duplicação
                if db.session.scalar(select(Instrutor).where(Instrutor.user_id == user.id)):
                    return False, "Já existe um instrutor com este e-mail."
                # Atualiza dados básicos (sem mexer na senha)
                if nome_completo:
                    user.nome_completo = nome_completo
                if nome_de_guerra:
                    user.nome_de_guerra = nome_de_guerra
                user.role = 'instrutor'
            else:
                # Criar novo usuário → exige senha
                if not password:
                    return False, "Senha é obrigatória para criar um novo usuário."
                user = User(
                    email=email,
                    username=email,
                    role='instrutor',
                    nome_completo=nome_completo or None,
                    nome_de_guerra=nome_de_guerra or None,
                    id_func=matricula or None
                )
                if hasattr(user, 'set_password'):
                    user.set_password(password)
                else:
                    user.password = password
                db.session.add(user)
                db.session.flush()

            # Cria o perfil de instrutor
            instrutor = Instrutor(
                user_id=user.id,
                matricula=matricula,
                especializacao='',   # defaults seguros para colunas legadas
                formacao=None,
                credor=None,
                posto_graduacao=posto,
                telefone=telefone,
                is_rr=is_rr
            )
            db.session.add(instrutor)

            # Vincula à escola
            if school_id:
                InstrutorService._ensure_user_school(user.id, int(school_id), role='instrutor')

            db.session.commit()
            return True, "Instrutor cadastrado com sucesso!"
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.exception("IntegrityError ao criar instrutor")
            return False, "Dados já existentes (verifique matrícula/e-mail)."
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Erro geral ao criar instrutor")
            return False, f"Ocorreu um erro ao criar o instrutor: {str(e)}"

    @staticmethod
    def get_instrutor_by_id(instrutor_id: int):
        return db.session.get(Instrutor, instrutor_id)

    @staticmethod
    def get_all_instrutores():
        stmt = select(Instrutor).order_by(Instrutor.id)
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

            # Atualiza dados do usuário associado
            user = db.session.get(User, instrutor.user_id)
            if user:
                if nome_completo:
                    user.nome_completo = nome_completo
                if nome_de_guerra:
                    user.nome_de_guerra = nome_de_guerra

            instrutor.telefone = (telefone or None)
            instrutor.posto_graduacao = posto

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
            # DisciplinaTurma: detectar colunas/relationships que existirem
            dt_conditions = []
            for cname in ('instrutor_id', 'instrutor_id_1', 'instrutor_id_2', 'instrutor_1_id', 'instrutor_2_id'):
                if hasattr(DisciplinaTurma, cname):
                    dt_conditions.append(getattr(DisciplinaTurma, cname) == instrutor_id)
            if hasattr(DisciplinaTurma, 'instrutor_1'):
                dt_conditions.append(DisciplinaTurma.instrutor_1.has(Instrutor.id == instrutor_id))
            if hasattr(DisciplinaTurma, 'instrutor_2'):
                dt_conditions.append(DisciplinaTurma.instrutor_2.has(Instrutor.id == instrutor_id))
            if dt_conditions:
                for row in db.session.query(DisciplinaTurma).filter(or_(*dt_conditions)).all():
                    db.session.delete(row)

            # Horario
            if hasattr(Horario, 'instrutor_id'):
                db.session.execute(delete(Horario).where(Horario.instrutor_id == instrutor_id))
            elif hasattr(Horario, 'instrutor'):
                for h in db.session.query(Horario).filter(Horario.instrutor.has(Instrutor.id == instrutor_id)).all():
                    db.session.delete(h)

            # Vínculos escola
            db.session.query(UserSchool).filter_by(user_id=instrutor.user_id).delete()

            # Perfil + usuário
            user = db.session.get(User, instrutor.user_id)
            db.session.delete(instrutor)
            if user:
                db.session.delete(user)

            db.session.commit()
            return True, "Instrutor e registros vinculados excluídos com sucesso."
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Erro ao excluir instrutor (cascade)")
            return False, f"Erro ao excluir instrutor: {str(e)}"
