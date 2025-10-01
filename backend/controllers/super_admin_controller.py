# backend/controllers/super_admin_controller.py

from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required
import secrets
import string
from utils.decorators import super_admin_required
from ..models.database import db
from ..models.school import School
from ..models.user import User
from ..models.user_school import UserSchool
from ..models.password_reset_request import PasswordResetRequest
from ..services.school_service import SchoolService
from ..services.user_service import UserService
from sqlalchemy import not_, func, case, or_
from sqlalchemy.orm import selectinload

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/super-admin')


@super_admin_bp.route('/dashboard', methods=['GET'])
@login_required
@super_admin_required
def dashboard():
    """Painel principal do Super Admin com métricas globais e atalhos."""
    all_schools = db.session.execute(
        db.select(School).order_by(School.nome)
    ).scalars().all()

    metrics = {
        'total_schools': db.session.scalar(db.select(func.count()).select_from(School)) or 0,
        'active_schools': db.session.scalar(
            db.select(func.count()).select_from(School).filter(School.is_active.is_(True))
        ) or 0,
        'total_admins': db.session.scalar(
            db.select(func.count()).select_from(User).filter(User.role == 'admin_escola')
        ) or 0,
        'global_users': db.session.scalar(db.select(func.count()).select_from(User)) or 0,
        'pending_resets': db.session.scalar(
            db.select(func.count()).select_from(PasswordResetRequest)
            .filter(PasswordResetRequest.status == PasswordResetRequest.STATUS_PENDING)
        ) or 0,
        'user_school_links': db.session.scalar(db.select(func.count()).select_from(UserSchool)) or 0,
    }

    schools_overview_rows = db.session.execute(
        db.select(
            School.id,
            School.nome,
            School.is_active,
            School.created_at,
            func.count(UserSchool.id).label('members'),
            func.coalesce(
                func.sum(case((UserSchool.role == 'admin_escola', 1), else_=0)),
                0,
            ).label('admins'),
        )
        .outerjoin(UserSchool)
        .group_by(School.id)
        .order_by(School.nome)
    ).all()

    schools_overview = [
        {
            'id': row.id,
            'nome': row.nome,
            'is_active': row.is_active,
            'created_at': row.created_at,
            'members': row.members,
            'admins': row.admins,
        }
        for row in schools_overview_rows
    ]

    recent_assignments = db.session.execute(
        db.select(UserSchool)
        .options(selectinload(UserSchool.user), selectinload(UserSchool.school))
        .order_by(UserSchool.created_at.desc())
        .limit(6)
    ).scalars().all()

    pending_reset_requests = db.session.execute(
        db.select(PasswordResetRequest)
        .options(selectinload(PasswordResetRequest.user))
        .filter(PasswordResetRequest.status == PasswordResetRequest.STATUS_PENDING)
        .order_by(PasswordResetRequest.created_at.asc())
        .limit(5)
    ).scalars().all()

    return render_template(
        'super_admin/dashboard.html',
        all_schools=all_schools,
        metrics=metrics,
        schools_overview=schools_overview,
        recent_assignments=recent_assignments,
        pending_reset_requests=pending_reset_requests,
    )


@super_admin_bp.route('/exit-view')
@login_required
@super_admin_required
def exit_view():
    session.pop('view_as_school_id', None)
    session.pop('view_as_school_name', None)
    flash('Você saiu do modo de visualização.', 'info')
    return redirect(url_for('super_admin.dashboard'))


@super_admin_bp.route('/schools', methods=['GET', 'POST'])
@login_required
@super_admin_required
def manage_schools():
    if request.method == 'POST':
        school_name = (request.form.get('school_name') or '').strip()
        if not school_name:
            flash('O nome da escola é obrigatório.', 'danger')
        else:
            success, message = SchoolService.create_school(school_name)
            flash(message, 'success' if success else 'danger')
        return redirect(url_for('super_admin.manage_schools'))

    schools = db.session.execute(
        db.select(School).order_by(School.nome)
    ).scalars().all()
    return render_template('super_admin/manage_schools.html', schools=schools)


@super_admin_bp.route('/schools/delete/<int:school_id>', methods=['POST'])
@login_required
@super_admin_required
def delete_school(school_id):
    success, message = SchoolService.delete_school(school_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('super_admin.manage_schools'))


@super_admin_bp.route('/assignments', methods=['GET', 'POST'])
@login_required
@super_admin_required
def manage_assignments():
    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')
        school_id = request.form.get('school_id')

        if not user_id or not school_id:
            flash('Selecione um usuário e uma escola válidos.', 'danger')
            return redirect(url_for('super_admin.manage_assignments'))

        if action == 'assign':
            role = request.form.get('role')
            success, message = UserService.assign_school_role(int(user_id), int(school_id), role)
            flash(message, 'success' if success else 'danger')
        elif action == 'remove':
            success, message = UserService.remove_school_role(int(user_id), int(school_id))
            flash(message, 'success' if success else 'danger')
        else:
            flash('Ação inválida.', 'danger')

        return redirect(url_for('super_admin.manage_assignments'))

    manageable_users_query = db.select(User).filter(
        not_(User.role.in_(['programador', 'super_admin']))
    ).order_by(User.nome_completo.nullslast(), User.username.nullslast())
    manageable_users = db.session.scalars(manageable_users_query).all()

    assignments = db.session.execute(
        db.select(UserSchool)
        .options(selectinload(UserSchool.user), selectinload(UserSchool.school))
        .order_by(UserSchool.created_at.desc())
    ).scalars().all()

    assigned_user_ids = {assignment.user_id for assignment in assignments}
    unassigned_users = [user for user in manageable_users if user.id not in assigned_user_ids]

    schools = db.session.execute(
        db.select(School).order_by(School.nome)
    ).scalars().all()

    return render_template(
        'super_admin/manage_assignments.html',
        users=manageable_users,
        schools=schools,
        assignments=assignments,
        unassigned_users=unassigned_users,
    )


@super_admin_bp.route('/create-administrator', methods=['POST'])
@login_required
@super_admin_required
def create_administrator():
    nome_completo = (request.form.get('nome_completo') or '').strip()
    email = (request.form.get('email') or '').strip()
    matricula = (request.form.get('matricula') or '').strip()
    school_id_raw = request.form.get('school_id')

    try:
        school_id = int(school_id_raw)
    except (TypeError, ValueError):
        school_id = None

    if not all([nome_completo, email, matricula, school_id]):
        flash('Todos os campos são obrigatórios.', 'danger')
        return redirect(url_for('super_admin.manage_schools'))

    existing_user = db.session.scalar(
        db.select(User).filter(
            or_(User.email == email, User.matricula == matricula)
        )
    )
    if existing_user:
        flash('Já existe um usuário com este e-mail ou matrícula.', 'danger')
        return redirect(url_for('super_admin.manage_schools'))

    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(10))

    new_user = User(
        nome_completo=nome_completo,
        email=email,
        matricula=matricula,
        role='admin_escola',
        is_active=True,
        must_change_password=True,
    )
    new_user.set_password(temp_password)

    db.session.add(new_user)
    db.session.flush()

    assignment = UserSchool(
        user_id=new_user.id,
        school_id=school_id,
        role='admin_escola',
    )
    db.session.add(assignment)

    try:
        db.session.commit()
        flash(
            f'Administrador "{nome_completo}" criado com sucesso! Senha temporária: {temp_password}',
            'success',
        )
    except Exception as exc:  # pragma: no cover - logging de erro já é suficiente
        db.session.rollback()
        flash(f'Erro ao criar administrador: {exc}', 'danger')

    return redirect(url_for('super_admin.manage_schools'))


@super_admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
@super_admin_required
def delete_user(user_id):
    success, message = UserService.delete_user_by_id(user_id)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('super_admin.manage_assignments'))
