# backend/app.py

import os
from importlib import import_module
from flask import Flask, render_template
import click
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel

from backend.extensions import limiter
from backend.config import Config
from backend.models.database import db
from backend.models.user import User
# Importações de todos os modelos para que o Flask-Migrate os reconheça
from backend.models.aluno import Aluno
from backend.models.disciplina import Disciplina
from backend.models.disciplina_turma import DisciplinaTurma
from backend.models.historico import HistoricoAluno
from backend.models.historico_disciplina import HistoricoDisciplina
from backend.models.horario import Horario
from backend.models.image_asset import ImageAsset
from backend.models.instrutor import Instrutor
from backend.models.password_reset_token import PasswordResetToken
from backend.models.school import School
from backend.models.semana import Semana
from backend.models.site_config import SiteConfig
from backend.models.turma import Turma
from backend.models.turma_cargo import TurmaCargo
from backend.models.user_school import UserSchool
from backend.services.asset_service import AssetService
# IMPORTAÇÃO DOS NOVOS MODELOS DE QUESTIONÁRIO
from backend.models.questionario import Questionario
from backend.models.pergunta import Pergunta
from backend.models.opcao_resposta import OpcaoResposta
from backend.models.resposta import Resposta


def create_app(config_class=Config):
    """
    Fábrica de aplicação: cria e configura a instância do Flask.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    template_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(config_class)

    # Executa a verificação da config (importante para produção)
    config_class.init_app(app)

    # Inicializa as extensões com a app
    db.init_app(app)
    Migrate(app, db)
    CSRFProtect(app)
    limiter.init_app(app)
    Babel(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Um contexto é necessário para registrar blueprints e outras configurações
    with app.app_context():
        AssetService.initialize_upload_folder(app)
        register_blueprints(app)
        register_handlers_and_processors(app)
        
    register_cli_commands(app)
    return app

def register_blueprints(app):
    """Importa e registra os blueprints na aplicação."""

    def _register(module_path: str, blueprint_name: str) -> None:
        module = import_module(module_path)
        blueprint = getattr(module, blueprint_name, None)
        if blueprint is None:
            app.logger.warning(
                "Blueprint '%s' não encontrado no módulo '%s'. Registro ignorado.",
                blueprint_name,
                module_path,
            )
            return
        app.register_blueprint(blueprint)

    for module_path, blueprint_name in [
        ('backend.controllers.auth_controller', 'auth_bp'),
        ('backend.controllers.aluno_controller', 'aluno_bp'),
        ('backend.controllers.instrutor_controller', 'instrutor_bp'),
        ('backend.controllers.disciplina_controller', 'disciplina_bp'),
        ('backend.controllers.historico_controller', 'historico_bp'),
        ('backend.controllers.main_controller', 'main_bp'),
        ('backend.controllers.assets_controller', 'assets_bp'),
        ('backend.controllers.customizer_controller', 'customizer_bp'),
        ('backend.controllers.horario_controller', 'horario_bp'),
        ('backend.controllers.semana_controller', 'semana_bp'),
        ('backend.controllers.turma_controller', 'turma_bp'),
        ('backend.controllers.vinculo_controller', 'vinculo_bp'),
        ('backend.controllers.user_controller', 'user_bp'),
        ('backend.controllers.relatorios_controller', 'relatorios_bp'),
        ('backend.controllers.super_admin_controller', 'super_admin_bp'),
        ('backend.controllers.admin_controller', 'admin_escola_bp'),
        ('backend.controllers.questionario_controller', 'questionario_bp'),
    ]:
        _register(module_path, blueprint_name)

def register_handlers_and_processors(app):
    """Registra hooks, context processors e error handlers."""
    @app.context_processor
    def inject_site_configs():
        from backend.services.site_config_service import SiteConfigService
        if app.config.get("TESTING", False):
            SiteConfigService.init_default_configs()
        configs = SiteConfigService.get_all_configs()
        return dict(site_config={c.config_key: c.config_value for c in configs})

    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

def register_cli_commands(app):
    """Registra os comandos de linha de comando."""
    @app.cli.command("create-super-admin")
    def create_super_admin():
        with app.app_context():
            super_admin_password = os.environ.get('SUPER_ADMIN_PASSWORD')
            if not super_admin_password:
                print("A variável de ambiente SUPER_ADMIN_PASSWORD não está definida.")
                return
            user = db.session.execute(db.select(User).filter_by(username='super_admin')).scalar_one_or_none()
            if user:
                print("Usuário 'super_admin' já existe. Atualizando senha e ativando...")
                user.is_active = True
                user.set_password(super_admin_password)
            else:
                print("Criando o usuário super administrador 'super_admin'...")
                # CORREÇÃO: trocado id_func por matricula
                user = User(
                    matricula='SUPER_ADMIN', 
                    username='super_admin', 
                    email='super_admin@escola.com.br', 
                    role='super_admin', 
                    is_active=True
                )
                user.set_password(super_admin_password)
                db.session.add(user)
            db.session.commit()
            print("Comando executado com sucesso!")

    @app.cli.command("create-programmer")
    def create_programmer():
        with app.app_context():
            prog_password = os.environ.get('PROGRAMMER_PASSWORD')
            if not prog_password:
                print("A variável de ambiente PROGRAMMER_PASSWORD não está definida.")
                return
            user = db.session.execute(db.select(User).filter_by(matricula='PROG001')).scalar_one_or_none()
            if user:
                print("O usuário 'programador' já existe.")
            else:
                print("Criando o usuário programador...")
                # CORREÇÃO: trocado id_func por matricula
                user = User(
                    matricula='PROG001', 
                    username='programador', 
                    email='dev@escola.com.br', 
                    role='programador', 
                    is_active=True
                )
                user.set_password(prog_password)
                db.session.add(user)
            db.session.commit()
            print("Usuário programador criado com sucesso!")

    @app.cli.command("clear-data")
    @click.option('--app', is_flag=True, help='Limpa apenas os dados da aplicação (alunos, turmas, etc).')
    def clear_data_command(app):
        """Apaga dados da aplicação, preservando a estrutura e os admins."""
        from scripts.clear_data import clear_transactional_data
        
        if not app:
             if input("ATENÇÃO: Este comando irá apagar TODOS os dados de alunos, turmas, etc. Deseja continuar? (s/n): ").lower() != 's':
                print("Operação cancelada.")
                return
        
        clear_transactional_data()
    
    # --- NOVO COMANDO PARA POPULAR O QUESTIONÁRIO ---
    @app.cli.command("seed-questionario")
    def seed_questionario_command():
        """Cria um questionário de exemplo no banco de dados."""
        from scripts.seed_questionario import seed_questionario_for_cli
        with app.app_context():
            seed_questionario_for_cli()
        print("Comando de popular questionário executado.")


# Este bloco só é executado quando o arquivo é chamado diretamente
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)