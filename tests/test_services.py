# tests/test_services.py

import pytest
from datetime import date, timedelta
from sqlalchemy import select
from backend.models.user import User
from backend.models.aluno import Aluno
from backend.models.instrutor import Instrutor
from backend.models.disciplina import Disciplina
from backend.models.turma import Turma
from backend.models.semana import Semana
from backend.models.horario import Horario
from backend.models.school import School
from backend.models.user_school import UserSchool
from backend.services.aluno_service import AlunoService
from backend.services.dashboard_service import DashboardService
from backend.services.turma_service import TurmaService
from backend.models.database import db

# ... (testes existentes que já passam) ...

class TestTurmaService:
    """
    Suíte de testes para o TurmaService.
    """

    def test_create_turma(self, test_app):
        """Testa se uma nova turma é criada com sucesso."""
        with test_app.app_context():
            school = School(nome="Escola Para Turmas")
            db.session.add(school)
            db.session.commit()

            turma_data = {'nome': 'Turma Teste 1', 'ano': 2025}
            
            # Ação
            success, message = TurmaService.create_turma(turma_data, school.id)

            # Asserções
            assert success is True
            assert message == "Turma cadastrada com sucesso!"
            turma_criada = db.session.scalar(select(Turma).filter_by(nome='Turma Teste 1'))
            assert turma_criada is not None
            assert turma_criada.school_id == school.id

    def test_update_turma_associates_students(self, test_app):
        """Testa se a atualização de uma turma associa e desassocia alunos corretamente."""
        with test_app.app_context():
            # Setup
            school = School(nome="Escola de Atualização")
            db.session.add(school)
            db.session.commit()

            turma = Turma(nome="Turma de Atualização", ano=2025, school_id=school.id)
            user1 = User(matricula='aluno1', nome_completo='Aluno Um')
            user2 = User(matricula='aluno2', nome_completo='Aluno Dois')
            db.session.add_all([turma, user1, user2])
            db.session.commit()

            aluno1 = Aluno(user_id=user1.id, opm="OPM1")
            aluno2 = Aluno(user_id=user2.id, opm="OPM2")
            db.session.add_all([aluno1, aluno2])
            db.session.commit()

            form_data = {
                'nome': 'Turma Atualizada',
                'ano': 2025,
                'alunos_ids': [aluno1.id]
            }

            # Ação
            TurmaService.update_turma(turma.id, form_data)

            # Asserções
            assert turma.nome == 'Turma Atualizada'
            assert len(turma.alunos) == 1
            assert turma.alunos[0].id == aluno1.id
            assert aluno1.turma_id == turma.id
            assert aluno2.turma_id is None

    def test_delete_turma(self, test_app):
        """Testa se uma turma é excluída corretamente."""
        with test_app.app_context():
            school = School(nome="Escola de Exclusão")
            db.session.add(school)
            db.session.commit()
            
            turma = Turma(nome="Turma a ser Excluída", ano=2025, school_id=school.id)
            db.session.add(turma)
            db.session.commit()
            turma_id = turma.id

            # Ação
            success, message = TurmaService.delete_turma(turma_id)

            # Asserções
            assert success is True
            assert "foram excluídos com sucesso" in message
            turma_excluida = db.session.get(Turma, turma_id)
            assert turma_excluida is None

class TestSchoolAndUserServices:
    """Testes adicionais para serviços críticos e regras de permissão."""

    def test_school_service_create_and_duplicate(self, test_app):
        with test_app.app_context():
            success, message = SchoolService.create_school('Escola Nova Cobertura')
            assert success
            assert 'criada com sucesso' in message
            duplicate, dup_message = SchoolService.create_school('Escola Nova Cobertura')
            assert not duplicate
            assert 'já existe' in dup_message
            empty, empty_message = SchoolService.create_school('')
            assert not empty
            assert 'não pode estar vazio' in empty_message

    def test_school_service_delete(self, test_app):
        with test_app.app_context():
            success, msg = SchoolService.delete_school(9999)
            assert not success
            escola = School(nome='Escola Remoção')
            db.session.add(escola)
            db.session.commit()
            deleted, deleted_msg = SchoolService.delete_school(escola.id)
            assert deleted
            assert 'excluídos com sucesso' in deleted_msg

    def test_user_service_assign_and_remove(self, test_app):
        with test_app.app_context():
            school = School(nome='Escola Usuário Serviço')
            user = User(matricula='usr_assign', username='usr_assign', role='aluno', is_active=True)
            db.session.add_all([school, user])
            db.session.commit()
            ok, message = UserService.assign_school_role(user.id, school.id, 'instrutor')
            assert ok
            assert 'instrutor' in message
            updated_user = db.session.get(User, user.id)
            assert updated_user.role == 'instrutor'
            assignment = db.session.scalar(select(UserSchool).filter_by(user_id=user.id, school_id=school.id))
            assert assignment is not None
            assert assignment.role == 'instrutor'
            removed, removed_message = UserService.remove_school_role(user.id, school.id)
            assert removed
            assert 'removido com sucesso' in removed_message
            assignment_after = db.session.scalar(select(UserSchool).filter_by(user_id=user.id, school_id=school.id))
            assert assignment_after is None

    def test_user_service_protects_special_accounts(self, test_app):
        with test_app.app_context():
            school = School(nome='Escola Proteção')
            super_user = User(matricula='sa_protect', username='super_admin', role='super_admin', is_active=True)
            programmer_user = User(matricula='prog_protect', username='programador', role='programador', is_active=True)
            db.session.add_all([school, super_user, programmer_user])
            db.session.commit()
            assign_super, assign_msg = UserService.assign_school_role(super_user.id, school.id, 'aluno')
            assert not assign_super
            assert 'Não é permitido' in assign_msg
            db.session.add(UserSchool(user_id=programmer_user.id, school_id=school.id, role='programador'))
            db.session.commit()
            remove_prog, remove_msg = UserService.remove_school_role(programmer_user.id, school.id)
            assert not remove_prog
            assert 'Não é permitido' in remove_msg
