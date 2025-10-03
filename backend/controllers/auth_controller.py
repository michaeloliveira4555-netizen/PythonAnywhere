# backend/controllers/auth_controller.py
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from backend.extensions import limiter  # noqa: F401

from ..models.database import db
from ..models.user import User
from ..models.user_school import UserSchool
from ..models.instrutor import Instrutor
from ..models.aluno import Aluno
from ..models.disciplina import Disciplina
from ..models.historico_disciplina import HistoricoDisciplina
from utils.validators import validate_email, validate_password_strength
from ..services.password_reset_service import PasswordResetService

auth_bp = Blueprint('auth', __name__)


class LoginForm(FlaskForm):
    username = StringField('Matrícula / Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')


@auth_bp.before_app_request
def enforce_password_change():
    if not current_user.is_authenticated:
        return None

    if not getattr(current_user, 'must_change_password', False):
        return None

    allowed = {
        'auth.force_change_password',
        'auth.logout',
        'static',
    }
    endpoint = request.endpoint or ''
    if endpoint not in allowed:
        return redirect(url_for('auth.force_change_password'))
    return None


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        matricula = request.form.get('matricula')
        nome_completo = request.form.get('nome_completo')
        nome_de_guerra = request.form.get('nome_de_guerra')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        role = request.form.get('role')
        opm = request.form.get('opm')
        posto_graduacao = request.form.get('posto_graduacao')

        if not role:
            flash('Por favor, selecione sua função (Aluno ou Instrutor).', 'danger')
            return render_template('register.html', form_data=request.form)

        if role == 'aluno' and not opm:
            flash('O campo OPM é obrigatório para alunos.', 'danger')
            return render_template('register.html', form_data=request.form)

        if not posto_graduacao:
            flash('O campo Posto/Graduação é obrigatório.', 'danger')
            return render_template('register.html', form_data=request.form)

        if not validate_email(email):
            flash('Formato de e-mail inválido.', 'danger')
            return render_template('register.html', form_data=request.form)

        is_strong, message = validate_password_strength(password)
        if not is_strong:
            flash(message, 'danger')
            return render_template('register.html', form_data=request.form)

        user = db.session.execute(
            db.select(User).filter_by(matricula=matricula, role=role)
        ).scalar_one_or_none()

        if not user:
            flash(
                'Matrícula não encontrada para a função selecionada. Contate a administração.', 'danger'
            )
            return render_template('register.html', form_data=request.form)

        if user.is_active:
            flash('Esta conta já foi ativada. Tente fazer o login.', 'info')
            return redirect(url_for('auth.login'))

        if password != password2:
            flash('As senhas não coincidem.', 'danger')
            return render_template('register.html', form_data=request.form)

        email_exists = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        if email_exists and email_exists.id != user.id:
            flash('Este e-mail já está em uso por outra conta.', 'danger')
            return render_template('register.html', form_data=request.form)

        user.nome_completo = nome_completo
        user.nome_de_guerra = nome_de_guerra
        user.posto_graduacao = posto_graduacao
        user.email = email
        user.username = matricula
        user.set_password(password)
        user.is_active = True

        if role == 'instrutor' and not user.instrutor_profile:
            new_instrutor_profile = Instrutor(user_id=user.id)
            db.session.add(new_instrutor_profile)
        elif role == 'aluno' and not user.aluno_profile:
            new_aluno_profile = Aluno(user_id=user.id, opm=opm)
            db.session.add(new_aluno_profile)
            db.session.flush()

            user_school_link = db.session.scalar(select(UserSchool).where(UserSchool.user_id == user.id))
            if user_school_link:
                school_id = user_school_link.school_id
                disciplinas_da_escola = db.session.scalars(
                    select(Disciplina).where(Disciplina.school_id == school_id)
                ).all()
                for disciplina in disciplinas_da_escola:
                    nova_matricula = HistoricoDisciplina(aluno_id=new_aluno_profile.id, disciplina_id=disciplina.id)
                    db.session.add(nova_matricula)

        db.session.commit()

        flash('Sua conta foi ativada com sucesso! Agora você pode fazer o login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form_data={})


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("8 per minute", methods=['POST'], error_message='Muitas tentativas. Tente novamente mais tarde.')
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login_identifier = form.username.data
        password = form.password.data

        user = db.session.execute(db.select(User).filter_by(matricula=login_identifier)).scalar_one_or_none()

        if not user:
            user = db.session.execute(db.select(User).filter_by(username=login_identifier)).scalar_one_or_none()

        if user and user.is_active and user.check_password(password):
            login_user(user)
            if getattr(user, 'must_change_password', False):
                flash('Use uma nova senha para continuar.', 'warning')
                return redirect(url_for('auth.force_change_password'))
            return redirect(url_for('main.dashboard'))
        elif user and not user.is_active:
            flash(
                'Sua conta precisa ser ativada. Use a página de registro para ativá-la.', 'warning'
            )
        else:
            flash('Matrícula/Usuário ou senha inválidos.', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit(
    "4 per minute", methods=['POST'], error_message='Muitas solicitações de redefinição. Tente novamente mais tarde.'
)
def forgot_password():
    if request.method == 'POST':
        matricula = (request.form.get('matricula') or '').strip()
        if not matricula:
            flash('Informe a matrícula do usuário.', 'warning')
            return render_template('forgot_password.html', form_data=request.form)

        success, message = PasswordResetService.request_password_reset(matricula)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('auth.login'))
        return render_template('forgot_password.html', form_data=request.form)

    return render_template('forgot_password.html', form_data={})


@auth_bp.route('/force-change-password', methods=['GET', 'POST'])
@login_required
def force_change_password():
    if not getattr(current_user, 'must_change_password', False):
        flash('Senha já atualizada.', 'info')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password_confirm = request.form.get('password2', '')

        if not password or not password_confirm:
            flash('Preencha os dois campos de senha.', 'warning')
            return render_template('force_change_password.html', form_data=request.form)

        if password != password_confirm:
            flash('As senhas informadas não coincidem.', 'danger')
            return render_template('force_change_password.html', form_data=request.form)

        is_strong, message = validate_password_strength(password)
        if not is_strong:
            flash(message, 'danger')
            return render_template('force_change_password.html', form_data=request.form)

        current_user.set_password(password)
        current_user.must_change_password = False
        db.session.commit()

        flash('Senha atualizada com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('force_change_password.html', form_data={})
