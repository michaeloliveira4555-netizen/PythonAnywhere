# backend/controllers/auth_controller.py
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

from ..models.database import db
from ..models.user import User
from ..models.user_school import UserSchool
from ..models.instrutor import Instrutor
from ..models.aluno import Aluno
# --- NOVAS IMPORTAÇÕES NECESSÁRIAS ---
from ..models.disciplina import Disciplina
from ..models.historico_disciplina import HistoricoDisciplina
from utils.validators import validate_email, validate_password_strength
from ..services.password_reset_service import PasswordResetService

auth_bp = Blueprint('auth', __name__)

# Define o formulário de login
class LoginForm(FlaskForm):
    username = StringField('Matrícula / Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

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

        if not role:
            flash('Por favor, selecione sua função (Aluno ou Instrutor).', 'danger')
            return render_template('register.html', form_data=request.form)

        if role == 'aluno' and not opm:
            flash('O campo OPM é obrigatório para alunos.', 'danger')
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
            flash('Matrícula não encontrada para a função selecionada. Contate a administração.', 'danger')
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
        user.email = email
        user.username = matricula
        user.set_password(password)
        user.is_active = True
        
        # --- LÓGICA DE CRIAÇÃO DE PERFIL E MATRÍCULA AUTOMÁTICA ---
        if role == 'instrutor' and not user.instrutor_profile:
            new_instrutor_profile = Instrutor(user_id=user.id)
            db.session.add(new_instrutor_profile)
        elif role == 'aluno' and not user.aluno_profile:
            # 1. Cria o perfil do aluno
            new_aluno_profile = Aluno(user_id=user.id, opm=opm)
            db.session.add(new_aluno_profile)
            db.session.flush() # Garante que o perfil do aluno tenha um ID

            # 2. Encontra a escola do aluno
            user_school_link = db.session.scalar(select(UserSchool).where(UserSchool.user_id == user.id))
            if user_school_link:
                school_id = user_school_link.school_id
                # 3. Encontra todas as disciplinas dessa escola
                disciplinas_da_escola = db.session.scalars(select(Disciplina).where(Disciplina.school_id == school_id)).all()
                # 4. Matricula o aluno em cada disciplina
                for disciplina in disciplinas_da_escola:
                    nova_matricula = HistoricoDisciplina(aluno_id=new_aluno_profile.id, disciplina_id=disciplina.id)
                    db.session.add(nova_matricula)
        # --- FIM DA CORREÇÃO ---
        
        db.session.commit()

        flash('Sua conta foi ativada com sucesso! Agora você pode fazer o login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form_data={})


@auth_bp.route('/login', methods=['GET', 'POST'])
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

            if user.role == 'super_admin':
                return redirect(url_for('super_admin.dashboard'))
            
            if user.role == 'aluno' and not user.aluno_profile:
                flash('Por favor, complete seu perfil de aluno para continuar.', 'info')
                return redirect(url_for('aluno.completar_cadastro'))

            elif user.role == 'instrutor' and not user.instrutor_profile:
                flash('Por favor, complete seu perfil de instrutor para continuar.', 'info')
                return redirect(url_for('instrutor.completar_cadastro'))

            return redirect(url_for('main.dashboard'))
        elif user and not user.is_active:
            flash('Sua conta precisa ser ativada. Use a página de registro para ativá-la.', 'warning')
        else:
            flash('Matrícula/Usuário ou senha inválidos.', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/set-new-with-token', methods=['GET', 'POST'])
def set_new_with_token():
    if request.method == 'POST':
        matricula = request.form.get('matricula', '').strip()
        raw_token = request.form.get('token', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not matricula or not raw_token or not password or not password2:
            flash('Preencha todos os campos.', 'danger')
            return render_template('set_new_with_token.html', form_data=request.form)

        if password != password2:
            flash('As senhas não coincidem.', 'danger')
            return render_template('set_new_with_token.html', form_data=request.form)

        is_strong, message = validate_password_strength(password)
        if not is_strong:
            flash(message, 'danger')
            return render_template('set_new_with_token.html', form_data=request.form)
        
        user = PasswordResetService.consume_with_user_and_raw_token(matricula, raw_token)
        if not user:
            flash('Token inválido, expirado ou dados incorretos.', 'danger')
            return render_template('set_new_with_token.html', form_data=request.form)

        user.set_password(password)
        user.must_change_password = False
        db.session.commit()
        flash('Senha redefinida com sucesso. Faça o login com a nova senha.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('set_new_with_token.html', form_data={})