# backend/config.py

import os
basedir = os.path.abspath(os.path.dirname(__file__))
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'd2a1b9c8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'escola.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BABEL_DEFAULT_LOCALE = 'pt_BR'
    # Segurança: configurações de cookies e sessão.
    # Em produção defina SESSION_COOKIE_SECURE=True e REMEMBER_COOKIE_SECURE=True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')  # 'Lax' é bom por padrão
    # Por padrão consideramos secure=True em ambiente de produção
    if os.environ.get('SESSION_COOKIE_SECURE') is not None:
        SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE') == 'True'
    else:
        SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV', '').lower() == 'production'

    REMEMBER_COOKIE_HTTPONLY = True
    if os.environ.get('REMEMBER_COOKIE_SECURE') is not None:
        REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE') == 'True'
    else:
        REMEMBER_COOKIE_SECURE = os.environ.get('FLASK_ENV', '').lower() == 'production'

    # Tempo padrão de validade da sessão (em dias)
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ.get('PERMANENT_SESSION_LIFETIME_DAYS', '7')))

    @staticmethod
    def init_app(app):
        """
        Executa verificações de configuração depois que a app foi criada.
        Isso evita erros durante a importação em ambientes de teste.
        """
        if not app.config.get("SECRET_KEY") and not app.testing:
            raise ValueError("No SECRET_KEY set for Flask application. Set the SECRET_KEY environment variable.")