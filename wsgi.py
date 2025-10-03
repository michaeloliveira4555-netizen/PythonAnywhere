"""WSGI entrypoint para Gunicorn em produção.

Cria a aplicação usando a factory `create_app` e expõe a variável `app`.
"""
from backend.app import create_app

app = create_app()
