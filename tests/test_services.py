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
from backend.services.password_reset_service import PasswordResetService
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

class TestPasswordResetWorkflow:
    """Cenários para recuperação de senha mediada pelo administrador."""

    def test_request_and_process_reset(self, test_app):
        with test_app.app_context():
            school = School(nome='Escola Recuperação')
            db.session.add(school)
            db.session.commit()

            admin = User(matricula='admin_reset', nome_completo='Admin Reset', role='admin_escola', is_active=True)
            user = User(matricula='usuario_reset', nome_completo='Usuário Reset', role='aluno', is_active=True)
            db.session.add_all([admin, user])
            db.session.commit()

            db.session.add_all([
                UserSchool(user_id=admin.id, school_id=school.id, role='admin_escola'),
                UserSchool(user_id=user.id, school_id=school.id, role='aluno'),
            ])
            db.session.commit()

            success, message = PasswordResetService.request_password_reset(user.matricula)
            assert success is True
            assert 'solic' in message.lower()

            requests = PasswordResetService.get_requests_for_admin(admin, status=PasswordResetService.STATUS_PENDING)
            assert len(requests) == 1
            req = requests[0]

            ok, msg, temp_password = PasswordResetService.process_request(req.id, admin)
            assert ok is True
            assert temp_password
            db.session.refresh(user)
            db.session.refresh(req)
            assert user.must_change_password is True
            assert user.check_password(temp_password) is True
            assert req.status == PasswordResetService.STATUS_COMPLETED

            remaining = PasswordResetService.get_requests_for_admin(admin, status=PasswordResetService.STATUS_PENDING)
            assert all(r.user_id != user.id for r in remaining)
