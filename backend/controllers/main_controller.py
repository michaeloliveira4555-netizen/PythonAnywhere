# backend/controllers/main_controller.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from ..models.school import School
from ..models.database import db
from ..services.dashboard_service import DashboardService
from utils.decorators import admin_or_programmer_required
from ..services.user_service import UserService

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ['super_admin', 'programador']:
        session.pop('view_as_school_id', None)
        session.pop('view_as_school_name', None)

    view_as_school_id = request.args.get('view_as_school', type=int)

    if current_user.role in ['super_admin', 'programador'] and view_as_school_id:
        school = db.session.get(School, view_as_school_id)
        if school:
            session['view_as_school_id'] = school.id
            session['view_as_school_name'] = school.nome
        else:
            flash("Escola selecionada para visualização não encontrada.", "danger")
            return redirect(url_for('super_admin.dashboard'))

    school_id_to_load = None
    if current_user.role in ['super_admin', 'programador']:
        school_id_to_load = session.get('view_as_school_id')
    elif hasattr(current_user, 'schools') and current_user.schools:
        school_id_to_load = current_user.schools[0].id

    dashboard_data = DashboardService.get_dashboard_data(school_id=school_id_to_load)

    school_in_context = None
    if school_id_to_load:
        school_in_context = db.session.get(School, school_id_to_load)

    return render_template('dashboard.html',
                           dashboard_data=dashboard_data,
                           school_in_context=school_in_context)


@main_bp.route('/pre-cadastro', methods=['GET', 'POST'])
@login_required
@admin_or_programmer_required
def pre_cadastro():
    role_arg = request.args.get('role')

    if request.method == 'POST':
        if current_user.role == 'super_admin':
            flash('Super Administradores possuem acesso somente leitura fora do painel do Super Admin.', 'warning')
            return redirect(url_for('super_admin.dashboard'))
        school_id = UserService.get_current_school_id()
        if not school_id:
            if current_user.role == 'super_admin':
                flash('Selecione uma escola no painel do Super Admin antes de realizar pré-cadastros.', 'warning')
                return redirect(url_for('super_admin.dashboard'))
            flash('Não foi possível identificar a escola do administrador. Ação cancelada.', 'danger')
            return redirect(url_for('main.pre_cadastro', role=role_arg))

        form_data = request.form.to_dict()
        if role_arg and not form_data.get('role'):
            form_data['role'] = role_arg

        matriculas_raw = form_data.get('matriculas', '').strip()
        if any(sep in matriculas_raw for sep in ('/', ' ', ',', ';')):
            partes = [
                p.strip() for p in matriculas_raw.replace(',', ' ').replace(';', ' ').split() if p.strip()
            ]
            matriculas = [p for p in partes if p.isdigit()]

            if not form_data.get('role'):
                flash('Função não informada para pré-cadastro em lote.', 'danger')
                return redirect(
                    url_for('main.pre_cadastro', role=role_arg) if role_arg else url_for('main.pre_cadastro')
                )

            success, novos, existentes = UserService.batch_pre_register_users(
                matriculas, form_data['role'], school_id
            )
            if success:
                flash(f'Pré-cadastro realizado: {novos} novo(s), {existentes} já existente(s).', 'success')
            else:
                flash('Falha ao pré-cadastrar usuários em lote.', 'danger')
            return redirect(url_for('main.pre_cadastro', role=role_arg) if role_arg else url_for('main.pre_cadastro'))
        else:
            form_data['matricula'] = matriculas_raw
            success, message = UserService.pre_register_user(form_data, school_id)
            flash(message, 'success' if success else 'danger')
            return redirect(url_for('main.pre_cadastro', role=role_arg) if role_arg else url_for('main.pre_cadastro'))

    schools = db.session.query(School).order_by(School.nome).all()
    return render_template('pre_cadastro.html', role_predefinido=role_arg, schools=schools)
