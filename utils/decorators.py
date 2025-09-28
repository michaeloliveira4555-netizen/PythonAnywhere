# utils/decorators.py

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def programmer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if getattr(current_user, 'role', None) != 'programador':
            flash('Acesso restrito para programadores.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        user_role = getattr(current_user, 'role', None)
        if user_role not in ['super_admin']:
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def school_admin_or_programmer_required(f):
    """
    NOVO DECORADOR: Permite acesso apenas para Admin da Escola e Programador.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        user_role = getattr(current_user, 'role', None)
        if user_role not in ['programador', 'admin_escola']:
            flash('Você não tem permissão para executar esta ação.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_or_programmer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        user_role = getattr(current_user, 'role', None)
        if user_role not in ['super_admin', 'programador', 'admin_escola']:
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_escola_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if getattr(current_user, 'role', None) != 'admin_escola':
            flash('Acesso restrito para administradores de escola.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def aluno_profile_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role == 'aluno':
            if not (hasattr(current_user, 'aluno_profile') and current_user.aluno_profile):
                flash('Para continuar, por favor, complete seu perfil de aluno.', 'info')
                return redirect(url_for('aluno.completar_cadastro'))
        return f(*args, **kwargs)
    return decorated_function