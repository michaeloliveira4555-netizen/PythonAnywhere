# tests/test_disciplina_service.py

import pytest
from sqlalchemy import select

from backend.services.disciplina_service import DisciplinaService
from backend.models.database import db
from backend.models.disciplina import Disciplina
from backend.models.historico_disciplina import HistoricoDisciplina
from backend.models.disciplina_turma import DisciplinaTurma
from backend.models.aluno import Aluno
from backend.models.turma import Turma
from backend.models.ciclo import Ciclo


class TestDisciplinaService:
    """Suíte de testes para o DisciplinaService."""

    def test_create_disciplina_and_associates_with_existing_students(self, db_session, setup_school_with_users):
        """Verifica criação da disciplina e associação automática com os alunos."""
        school, admin_user, alunos, ciclo_base = setup_school_with_users

        disciplina_data = {
            'materia': 'Ordem Unida',
            'carga_horaria_prevista': 30,
            'ciclo_id': ciclo_base.id,
        }

        success, message = DisciplinaService.create_disciplina(disciplina_data, school.id)

        assert success is True
        assert "associada aos alunos da escola" in message

        disciplina_criada = db_session.scalar(select(Disciplina).filter_by(materia='Ordem Unida'))
        assert disciplina_criada is not None
        assert disciplina_criada.school_id == school.id
        assert disciplina_criada.ciclo_id == ciclo_base.id

        total_alunos_escola = db_session.scalar(
            select(db.func.count(Aluno.id)).join(Turma).where(Turma.school_id == school.id)
        )
        total_matriculas = db_session.scalar(
            select(db.func.count(HistoricoDisciplina.id)).where(HistoricoDisciplina.disciplina_id == disciplina_criada.id)
        )
        assert total_matriculas == total_alunos_escola == len(alunos)

    def test_update_disciplina(self, db_session, setup_school_with_users):
        """Garante atualização dos dados de uma disciplina existente."""
        school, _, _, ciclo_base = setup_school_with_users

        novo_ciclo = Ciclo(nome='Ciclo Base 2')
        db_session.add(novo_ciclo)
        db_session.commit()

        disciplina = Disciplina(
            materia="Tiro Defensivo",
            carga_horaria_prevista=40,
            ciclo_id=ciclo_base.id,
            school_id=school.id,
        )
        db_session.add(disciplina)
        db_session.commit()

        update_data = {
            'materia': 'Tiro Policial',
            'carga_horaria_prevista': 50,
            'ciclo_id': novo_ciclo.id,
        }

        success, message = DisciplinaService.update_disciplina(disciplina.id, update_data)

        assert success is True
        assert message == "Disciplina atualizada com sucesso!"
        db_session.refresh(disciplina)
        assert disciplina.materia == 'Tiro Policial'
        assert disciplina.carga_horaria_prevista == 50
        assert disciplina.ciclo_id == novo_ciclo.id

    def test_delete_disciplina_cascades(self, db_session, setup_school_with_users):
        """Confere exclusão em cascata de vínculos ao remover uma disciplina."""
        school, _, alunos, ciclo_base = setup_school_with_users
        aluno1, aluno2 = alunos

        disciplina = Disciplina(
            materia="Defesa Pessoal",
            carga_horaria_prevista=25,
            ciclo_id=ciclo_base.id,
            school_id=school.id,
        )
        db_session.add(disciplina)
        db_session.commit()
        disciplina_id = disciplina.id

        matricula1 = HistoricoDisciplina(aluno_id=aluno1.id, disciplina_id=disciplina_id)
        vinculo_turma = DisciplinaTurma(pelotao=aluno1.turma.nome, disciplina_id=disciplina_id)
        db_session.add_all([matricula1, vinculo_turma])
        db_session.commit()

        assert db_session.get(HistoricoDisciplina, matricula1.id) is not None
        assert db_session.get(DisciplinaTurma, vinculo_turma.id) is not None

        success, message = DisciplinaService.delete_disciplina(disciplina_id)

        assert success is True
        assert "registros associados foram excluídos" in message
        assert db_session.get(Disciplina, disciplina_id) is None
        assert db_session.get(HistoricoDisciplina, matricula1.id) is None
        assert db_session.get(DisciplinaTurma, vinculo_turma.id) is None

    def test_get_disciplinas_agrupadas_por_ciclo(self, db_session, setup_school_with_users):
        """Valida agrupamento das disciplinas por ciclo."""
        school, _, _, _ = setup_school_with_users

        ciclo1 = Ciclo(nome='Ciclo 1')
        ciclo2 = Ciclo(nome='Ciclo 2')
        db_session.add_all([ciclo1, ciclo2])
        db_session.commit()

        d1_c1 = Disciplina(materia="Legislação I", carga_horaria_prevista=20, ciclo_id=ciclo1.id, school_id=school.id)
        d2_c1 = Disciplina(materia="Armamento e Munição", carga_horaria_prevista=30, ciclo_id=ciclo1.id, school_id=school.id)
        d1_c2 = Disciplina(materia="Legislação II", carga_horaria_prevista=20, ciclo_id=ciclo2.id, school_id=school.id)
        db_session.add_all([d1_c1, d2_c1, d1_c2])
        db_session.commit()

        disciplinas_agrupadas = DisciplinaService.get_disciplinas_agrupadas_por_ciclo(school.id)

        assert 'Ciclo 1' in disciplinas_agrupadas
        assert 'Ciclo 2' in disciplinas_agrupadas
        assert len(disciplinas_agrupadas['Ciclo 1']) == 2
        assert len(disciplinas_agrupadas['Ciclo 2']) == 1

        materias_ciclo1 = [item['disciplina'].materia for item in disciplinas_agrupadas['Ciclo 1']]
        assert materias_ciclo1 == ['Armamento e Munição', 'Legislação I']
        assert disciplinas_agrupadas['Ciclo 2'][0]['disciplina'].materia == 'Legislação II'
