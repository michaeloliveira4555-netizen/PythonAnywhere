from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from backend.models.database import db
from backend.models.school import School
from backend.models.user import User
from utils.decorators import admin_or_programmer_required
from ..services.user_service import UserService
from ..services.password_reset_service import PasswordResetService

admin_escola_bp = Blueprint('admin_escola', __name__, url_prefix='/admin-escola')


@admin_escola_bp.route('/pre-cadastro', methods=['GET', 'POST'])
@login_required
@admin_or_programmer_required
def pre_cadastro():
    if request.method == 'POST':
        matriculas_raw = request.form.get('matriculas')
        role = request.form.get('role')
        school_id = request.form.get('school_id')  # Usado pelo Super Admin

        if current_user.role == 'admin_escola':
            if current_user.user_schools:
                school_id = current_user.user_schools[0].school_id
            else:
                flash('Você não está associado a nenhuma escola para realizar o pré-cadastro.', 'danger')
                return redirect(url_for('main.dashboard'))

        if not matriculas_raw or not role or not school_id:
            flash('Por favor, preencha todos os campos, incluindo a escola.', 'danger')
            return redirect(url_for('admin_escola.pre_cadastro'))

        matriculas = [m.strip() for m in matriculas_raw.replace(',', ' ').replace(';', ' ').split() if m.strip()]

        success, novos, existentes = UserService.batch_pre_register_users(matriculas, role, school_id)

        if success:
            if novos:
                flash(f'{novos} novo(s) usuário(s) pré-cadastrado(s) com sucesso na escola correta!', 'success')
            if existentes:
                flash(f'{existentes} identificador(es) já existia(m) e foram ignorado(s).', 'info')
        else:
            flash('Erro ao pré-cadastrar usuários.', 'danger')

        return redirect(url_for('main.dashboard'))

    schools = db.session.query(School).order_by(School.nome).all()
    return render_template('pre_cadastro.html', schools=schools)


@admin_escola_bp.route('/reset-requests', methods=['GET'])
@login_required
@admin_or_programmer_required
def reset_requests():
    status = request.args.get('status', PasswordResetService.STATUS_PENDING)
    requests = PasswordResetService.get_requests_for_admin(current_user, status=status)
    return render_template('admin/reset_requests.html', reset_requests=requests, status=status)


@admin_escola_bp.route('/reset-requests/<int:request_id>/process', methods=['POST'])
@login_required
@admin_or_programmer_required
def process_reset_request(request_id: int):
    success, message, temp_password = PasswordResetService.process_request(request_id, current_user)
    if success and temp_password:
        flash(f'{message} Senha temporária: {temp_password}', 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('admin_escola.reset_requests'))


@admin_escola_bp.route('/reset-requests/<int:request_id>/cancel', methods=['POST'])
@login_required
@admin_or_programmer_required
def cancel_reset_request(request_id: int):
    success, message = PasswordResetService.cancel_request(request_id, current_user)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin_escola.reset_requests'))
