# tests/test_controllers.py

import pytest
from sqlalchemy import select
from datetime import date, timedelta
from flask import session
from backend.models.user import User
from backend.models.school import School
from backend.models.user_school import UserSchool
from backend.models.aluno import Aluno
from backend.models.instrutor import Instrutor
from backend.models.turma import Turma
from backend.models.disciplina import Disciplina
from backend.models.disciplina_turma import DisciplinaTurma
from backend.models.semana import Semana
from backend.models.ciclo import Ciclo
from backend.models.horario import Horario
from backend.models.database import db

class TestAuthController:
    """Testes para o fluxo de autenticação."""
    # ... (os testes de login que já passam) ...
    def test_login_redirects_to_complete_profile_for_new_student(self, test_client, test_app):
        pass # Placeholder for existing test
    def test_login_failure_wrong_password(self, test_client, test_app):
        pass # Placeholder for existing test

class TestPermissionSystem:
<<<<<<< HEAD
    """Testes para o sistema de permissões."""

    def test_super_admin_pre_cadastro_is_read_only(self, test_client, test_app):
        with test_app.app_context():
            super_admin = User(matricula='super_sa', username='super_sa', email='super@admin.com', role='super_admin', is_active=True)
            super_admin.set_password('superpass')
            escola = School(nome='Escola Central')
            db.session.add_all([super_admin, escola])
            db.session.commit()
            escola_id = escola.id
        with test_client as client:
            client.post('/login', data={'username': 'super_sa', 'password': 'superpass'}, follow_redirects=True)
            response_get = client.get('/pre-cadastro')
            assert response_get.status_code == 200
            response_post = client.post('/pre-cadastro', data={'matriculas': '99999', 'school_id': str(escola_id), 'role': 'aluno'}, follow_redirects=True)
            assert response_post.status_code == 200
            assert 'somente leitura' in response_post.get_data(as_text=True)
        with test_app.app_context():
            assert db.session.scalar(select(User).filter_by(matricula='99999')) is None

    def test_super_admin_cannot_approve_horario(self, test_client, test_app):
        with test_app.app_context():
            super_admin = User(matricula='super_sa_sched', username='super_sa_sched', email='dash@admin.com', role='super_admin', is_active=True)
            super_admin.set_password('superpass')
            escola = School(nome='Escola Agenda')
            ciclo = Ciclo(nome='Ciclo Agenda')
=======
    """Testes para o sistema de permissões e perfis especiais."""

    def _login(self, client, username, password):
        return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

    def test_super_admin_pre_cadastro_read_only(self, test_client, test_app):
        with test_app.app_context():
            super_admin = User(matricula='sa_perm', username='sa_perm', email='sa@admin.com', role='super_admin', is_active=True)
            super_admin.set_password('superpass')
            escola = School(nome='Escola Permissão')
            db.session.add_all([super_admin, escola])
            db.session.commit()
            escola_id = escola.id

        with test_client as client:
            self._login(client, 'sa_perm', 'superpass')
            get_response = client.get('/pre-cadastro')
            assert get_response.status_code == 200
            post_response = client.post('/pre-cadastro', data={'matriculas': '99999', 'school_id': str(escola_id), 'role': 'aluno'}, follow_redirects=True)
            assert post_response.status_code == 200
            assert 'somente leitura' in post_response.get_data(as_text=True)

        with test_app.app_context():
            created = db.session.scalar(select(User).filter_by(matricula='99999'))
            assert created is None

    def test_super_admin_blocked_on_admin_pre_cadastro(self, test_client, test_app):
        with test_app.app_context():
            super_admin = User(matricula='sa_admin', username='sa_admin', email='dash@admin.com', role='super_admin', is_active=True)
            super_admin.set_password('superpass')
            escola = School(nome='Escola Painel Admin')
            db.session.add_all([super_admin, escola])
            db.session.commit()

        with test_client as client:
            self._login(client, 'sa_admin', 'superpass')
            response = client.post('/admin-escola/pre-cadastro', data={'matriculas': '12345', 'role': 'aluno', 'school_id': '1'}, follow_redirects=True)
            assert response.status_code == 200
            assert 'somente leitura' in response.get_data(as_text=True)

        with test_app.app_context():
            assert db.session.scalar(select(User).filter_by(matricula='12345')) is None

    def test_admin_pre_cadastro_uses_own_school(self, test_client, test_app):
        with test_app.app_context():
            school = School(nome='Escola Admin Local')
            admin_user = User(matricula='adm_local', username='adm_local', email='admin@local.com', role='admin_escola', is_active=True)
            admin_user.set_password('adminpass')
            db.session.add_all([school, admin_user])
            db.session.commit()
            db.session.add(UserSchool(user_id=admin_user.id, school_id=school.id, role='admin_escola'))
            db.session.commit()

        with test_client as client:
            self._login(client, 'adm_local', 'adminpass')
            response = client.post('/admin-escola/pre-cadastro', data={'matriculas': '20001 20002', 'role': 'aluno'}, follow_redirects=True)
            assert response.status_code == 200
            assert 'sucesso' in response.get_data(as_text=True).lower()

        with test_app.app_context():
            created_users = db.session.scalars(select(User).filter(User.matricula.in_(['20001', '20002']))).all()
            assert len(created_users) == 2
            for created in created_users:
                link = db.session.scalar(select(UserSchool).filter_by(user_id=created.id, school_id=school.id))
                assert link is not None
                assert link.role == 'aluno'

    def test_super_admin_cannot_approve_horario(self, test_client, test_app):
        with test_app.app_context():
            super_admin = User(matricula='sa_sched', username='sa_sched', email='sched@admin.com', role='super_admin', is_active=True)
            super_admin.set_password('superpass')
            escola = School(nome='Escola Agenda Permissão')
            ciclo = Ciclo(nome='Ciclo Agenda Permissão')
>>>>>>> c400f4f (Limpeza de conflitos de merge e revisão visual)
            db.session.add_all([super_admin, escola, ciclo])
            db.session.commit()
            semana = Semana(nome='Semana Agenda', data_inicio=date.today(), data_fim=date.today() + timedelta(days=6), ciclo_id=ciclo.id)
            instrutor_user = User(matricula='instr_sched', username='instr_sched', role='instrutor', is_active=True)
            instrutor_user.set_password('instrpass')
            disciplina = Disciplina(materia='Disciplina Agenda', carga_horaria_prevista=10, school_id=escola.id, ciclo_id=ciclo.id)
            db.session.add_all([semana, instrutor_user, disciplina])
            db.session.commit()
            instrutor = Instrutor(user_id=instrutor_user.id, telefone=None, is_rr=False)
            db.session.add(instrutor)
            db.session.commit()
            horario = Horario(pelotao='Pel Agenda', dia_semana='segunda', periodo=1, duracao=1, semana_id=semana.id, disciplina_id=disciplina.id, instrutor_id=instrutor.id, status='pendente')
            db.session.add(horario)
            db.session.commit()
            horario_id = horario.id
<<<<<<< HEAD
        with test_client as client:
            client.post('/login', data={'username': 'super_sa_sched', 'password': 'superpass'}, follow_redirects=True)
            response_post = client.post('/horario/aprovar', data={'horario_id': horario_id, 'action': 'aprovar'}, follow_redirects=True)
            assert response_post.status_code == 200
            assert 'somente leitura' in response_post.get_data(as_text=True)
=======

        with test_client as client:
            self._login(client, 'sa_sched', 'superpass')
            response_post = client.post('/horario/aprovar', data={'horario_id': horario_id, 'action': 'aprovar'}, follow_redirects=True)
            assert response_post.status_code == 200
            assert 'somente leitura' in response_post.get_data(as_text=True)

>>>>>>> c400f4f (Limpeza de conflitos de merge e revisão visual)
        with test_app.app_context():
            horario_atualizado = db.session.get(Horario, horario_id)
            assert horario_atualizado.status == 'pendente'

class TestWorkflow:
    """
    Testes que validam fluxos de trabalho completos envolvendo múltiplos usuários.
    """
    def test_full_class_lifecycle(self, test_client, test_app):
        """
        Valida o ciclo de vida completo de uma aula.
        """
        with test_app.app_context():
            # --- 1. SETUP CORRIGIDO E EM ETAPAS ---
            # ETAPA A: Criar a entidade principal (Escola) e salvar para obter um ID.
            school = School(nome="Escola de Fluxo Completo")
            db.session.add(school)
            db.session.commit()

            # ETAPA B: Criar entidades que dependem da Escola.
            turma = Turma(nome="Pelotao-Workflow", ano=2025, school_id=school.id)
            ciclo = Ciclo(nome="Ciclo Workflow")
            db.session.add_all([turma, ciclo])
            db.session.commit()

            disciplina = Disciplina(materia="Teste de Workflow", carga_horaria_prevista=20, school_id=school.id, ciclo_id=ciclo.id)
            semana = Semana(nome="Semana Workflow", data_inicio=date.today(), data_fim=date.today() + timedelta(days=6), ciclo_id=ciclo.id)
            db.session.add_all([disciplina, semana])
            db.session.commit()

            # ETAPA C: Criar os usuários.
            instrutor_user = User(matricula='instrutor_wf', nome_de_guerra='Sgt Workflow', role='instrutor', is_active=True, posto_graduacao='Sargento')
            instrutor_user.set_password('pass1')
            admin_user = User(matricula='admin_wf', nome_de_guerra='Ten Workflow', role='admin_escola', is_active=True, posto_graduacao='Tenente')
            admin_user.set_password('pass2')
            aluno_user = User(matricula='aluno_wf', nome_de_guerra='Sd Workflow', role='aluno', is_active=True)
            aluno_user.set_password('pass3')
            db.session.add_all([instrutor_user, admin_user, aluno_user])
            db.session.commit()

            # ETAPA D: Criar os perfis e associações finais.
            instrutor = Instrutor(user_id=instrutor_user.id, telefone=None, is_rr=False)
            aluno = Aluno(user_id=aluno_user.id, opm='EsFAS', turma_id=turma.id)
            db.session.add_all([instrutor, aluno])
            db.session.commit()
            
            db.session.add_all([
                UserSchool(user_id=instrutor_user.id, school_id=school.id, role='instrutor'),
                UserSchool(user_id=admin_user.id, school_id=school.id, role='admin_escola'),
                UserSchool(user_id=aluno_user.id, school_id=school.id, role='aluno')
            ])
            vinculo = DisciplinaTurma(pelotao=turma.nome, disciplina_id=disciplina.id, instrutor_id_1=instrutor.id)
            db.session.add(vinculo)
            db.session.commit()

            # --- 2. Fluxo com sessões autenticadas ---
            with test_client as client:
                client.post('/login', data={'username': 'instrutor_wf', 'password': 'pass1'}, follow_redirects=True)
                with client.session_transaction() as sess:
                    assert sess.get('_user_id') == str(instrutor_user.id)
                aula_data = {'pelotao': turma.nome, 'semana_id': semana.id, 'dia': 'segunda', 'periodo': 3, 'disciplina_id': disciplina.id, 'duracao': 2}
                response_instrutor = client.post('/horario/salvar-aula', json=aula_data)
                assert response_instrutor.status_code == 200
                aula_criada = db.session.scalar(select(Horario).where(Horario.pelotao == turma.nome))
                assert aula_criada is not None
                assert aula_criada.status == 'pendente'
                client.get('/logout', follow_redirects=True)

                client.post('/login', data={'username': 'admin_wf', 'password': 'pass2'}, follow_redirects=True)
                response_admin = client.post('/horario/aprovar', data={'horario_id': aula_criada.id, 'action': 'aprovar'})
                assert response_admin.status_code == 302
                db.session.refresh(aula_criada)
                assert aula_criada.status == 'confirmado'
                client.get('/logout', follow_redirects=True)

                client.post('/login', data={'username': 'aluno_wf', 'password': 'pass3'}, follow_redirects=True)
                response_aluno = client.get('/horario/', query_string={'pelotao': turma.nome, 'semana_id': semana.id})
                assert response_aluno.status_code == 200
                assert b'Teste de Workflow' in response_aluno.data
                assert b'Sgt Workflow' in response_aluno.data
