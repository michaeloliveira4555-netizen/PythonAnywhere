# backend/models/__init__.py

# Importa a instância do banco de dados para que os modelos possam ser associados a ela
from .database import db

# Importa todos os modelos para garantir que sejam registrados no SQLAlchemy
from .user import User
from .school import School
from .user_school import UserSchool
from .aluno import Aluno
from .instrutor import Instrutor
from .turma import Turma
# IMPORTAÇÃO CORRIGIDA
from .ciclo import Ciclo
from .disciplina import Disciplina
from .disciplina_turma import DisciplinaTurma
from .horario import Horario
from .semana import Semana
from .historico import HistoricoAluno
from .historico_disciplina import HistoricoDisciplina
from .password_reset_token import PasswordResetToken
from .site_config import SiteConfig
from .image_asset import ImageAsset
from .turma_cargo import TurmaCargo
# IMPORTAÇÃO DOS NOVOS MODELOS
from .questionario import Questionario
from .pergunta import Pergunta
from .opcao_resposta import OpcaoResposta
from .resposta import Resposta


__all__ = [
    'db',
    'User',
    'School',
    'UserSchool',
    'Aluno',
    'Instrutor',
    'Turma',
    # EXPORTAÇÃO CORRIGIDA
    'Ciclo',
    'Disciplina',
    'DisciplinaTurma',
    'Horario',
    'Semana',
    'HistoricoAluno',
    'HistoricoDisciplina',
    'PasswordResetToken',
    'SiteConfig',
    'ImageAsset',
    'TurmaCargo',
    # EXPORTAÇÃO DOS NOVOS MODELOS
    'Questionario',
    'Pergunta',
    'OpcaoResposta',
    'Resposta'
]