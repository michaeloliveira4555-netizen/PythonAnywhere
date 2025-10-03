from __future__ import annotations
from typing import Optional as TypingOptional

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

from backend.models.database import db
from backend.models.instrutor import Instrutor
from backend.models.school import School
from backend.models.user import User
from backend.models.user_school import UserSchool
from backend.services.instrutor_service import InstrutorService
from backend.services.user_service import UserService
from utils.decorators import (
    can_view_management_pages_required,
    school_admin_or_programmer_required,
)

instrutor_bp = Blueprint('instrutor', __name__, url_prefix='/instrutor')

POSTOS_CHOICES = [
    ('Soldado PM', 'Soldado PM'),
    ('2º Sargento PM', '2º Sargento PM'),
    ('1º Sargento PM', '1º Sargento PM'),
    ('1º Tenente PM', '1º Tenente PM'),
    ('Capitão PM', 'Capitão PM'),
    ('Major PM', 'Major PM'),
    ('Tenente-Coronel PM', 'Tenente-Coronel PM'),
    ('Coronel PM', 'Coronel PM'),
    ('Outro', 'Outro'),
]


class DeleteForm(FlaskForm):
    submit = SubmitField('Excluir')


class InstrutorBaseForm(FlaskForm):
    nome_completo = StringField('Nome completo', validators=[Optional(), Length(max=255)])
    nome_de_guerra = StringField('Nome de guerra', validators=[Optional(), Length(max=255)])
    posto_graduacao_select = SelectField('Posto/Graduação', choices=POSTOS_CHOICES)
    posto_graduacao_outro = StringField('Outro (especifique)', validators=[Optional(), Length(max=100)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=30)])
    is_rr = BooleanField('RR')


class CadastroInstrutorForm(InstrutorBaseForm):
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(max=64)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[Optional(), Length(min=4)])
    submit = SubmitField('Salvar')


class EditarInstrutorForm(InstrutorBaseForm):
    submit = SubmitField('Salvar')


class CompletarInstrutorForm(InstrutorBaseForm):
    submit = SubmitField('Salvar')


def _resolve_school_id_for_user(user: User) -> TypingOptional[int]:
    if user and getattr(user, 'user_schools', None):
        for user_school in user.user_schools:
            return user_school.school_id
    sid = session.get('view_as_school_id')
    if sid:
        try:
            return int(sid)
        except (TypeError, ValueError):
            return None
    return None


def _ensure_school_id_for_current_user() -> TypingOptional[int]:
    if hasattr(current_user, 'id'):
        resolved = _resolve_school_id_for_user(current_user)
        if resolved:
            return resolved
    school_ids = [row[0] for row in db.session.execute(db.select(School.id)).all()]
    return school_ids[0] if len(school_ids) == 1 else None


@instrutor_bp.route('/')
@login_required
@can_view_management_pages_required
def listar_instrutores():
    instrutores = InstrutorService.get_all_instrutores()
    delete_form = DeleteForm()
    return render_template('listar_instrutores.html', instrutores=instrutores, form=delete_form)


@instrutor_bp.route('/cadastrar', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required
def cadastrar_instrutor():
    form = CadastroInstrutorForm()
    if request.method == 'POST' and form.validate_on_submit():
        payload = request.form.to_dict(flat=False)
        school_id = _ensure_school_id_for_current_user() or UserService.get_current_school_id()
        if not school_id:
            flash('Não foi possível identificar a escola para associar o instrutor.', 'danger')
            return redirect(url_for('instrutor.listar_instrutores'))

        existing_user = db.session.scalar(select(User).where(User.email == form.email.data))
        if existing_user:
            if existing_user.instrutor_profile:
                flash('Este usuário já possui perfil de instrutor.', 'warning')
                return redirect(url_for('instrutor.listar_instrutores'))

            ok, message = InstrutorService.create_profile_for_user(existing_user.id, payload)
            if ok:
                _sync_user_with_payload(existing_user, payload)
                _ensure_user_school_link(existing_user.id, school_id)
                db.session.commit()
                flash('Instrutor vinculado ao usuário existente com sucesso.', 'success')
                return redirect(url_for('instrutor.listar_instrutores'))
            flash(message, 'danger')
        else:
            if not payload.get('password'):
                flash('Informe uma senha para criar o novo instrutor.', 'danger')
            else:
                ok, message = InstrutorService.create_full_instrutor(payload, school_id)
                flash(message, 'success' if ok else 'danger')
                if ok:
                    return redirect(url_for('instrutor.listar_instrutores'))
    return render_template('cadastro_instrutor.html', form=form)


@instrutor_bp.route('/editar/<int:instrutor_id>', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required
def editar_instrutor(instrutor_id: int):
    instrutor = InstrutorService.get_instrutor_by_id(instrutor_id)
    if not instrutor:
        flash('Instrutor não encontrado.', 'danger')
        return redirect(url_for('instrutor.listar_instrutores'))

    form = EditarInstrutorForm()
    if request.method == 'GET':
        _populate_instrutor_form(form, instrutor)
    if request.method == 'POST' and form.validate_on_submit():
        ok, message = InstrutorService.update_instrutor(instrutor_id, request.form.to_dict(flat=False))
        flash(message, 'success' if ok else 'danger')
        if ok:
            return redirect(url_for('instrutor.listar_instrutores'))
    return render_template('editar_instrutor.html', form=form, instrutor=instrutor)


@instrutor_bp.route('/completar', methods=['GET', 'POST'])
@login_required
def completar_cadastro():
    form = CompletarInstrutorForm()
    profile: TypingOptional[Instrutor] = getattr(current_user, 'instrutor_profile', None)

    if request.method == 'POST' and form.validate_on_submit():
        payload = request.form.to_dict(flat=False)
        if profile:
            success, message = InstrutorService.update_instrutor(profile.id, payload)
        else:
            success, message = InstrutorService.create_profile_for_user(current_user.id, payload)
            if success:
                user = db.session.get(User, current_user.id)
                if user:
                    _sync_user_with_payload(user, payload)
                    db.session.commit()
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('main.dashboard'))
    else:
        if profile:
            _populate_instrutor_form(form, profile)
        else:
            form.nome_completo.data = current_user.nome_completo or ''
            form.nome_de_guerra.data = current_user.nome_de_guerra or ''
    return render_template('completar_cadastro_instrutor.html', form=form)


@instrutor_bp.route('/excluir/<int:instrutor_id>', methods=['POST'])
@login_required
@school_admin_or_programmer_required
def excluir_instrutor(instrutor_id: int):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash('Falha na validação do token CSRF.', 'danger')
        return redirect(url_for('instrutor.listar_instrutores'))
    ok, message = InstrutorService.delete_instrutor(instrutor_id)
    flash(message, 'success' if ok else 'danger')
    return redirect(url_for('instrutor.listar_instrutores'))


def _populate_instrutor_form(form: InstrutorBaseForm, instrutor: Instrutor) -> None:
    user = db.session.get(User, instrutor.user_id) if instrutor.user_id else None
    if user:
        form.nome_completo.data = user.nome_completo or ''
        form.nome_de_guerra.data = user.nome_de_guerra or ''
        posto_graduacao = getattr(user, 'posto_graduacao', None)
    else:
        posto_graduacao = None
    form.telefone.data = instrutor.telefone or ''
    allowed_postos = {choice[0] for choice in POSTOS_CHOICES}
    if posto_graduacao in allowed_postos:
        form.posto_graduacao_select.data = posto_graduacao
        form.posto_graduacao_outro.data = ''
    else:
        form.posto_graduacao_select.data = 'Outro'
        form.posto_graduacao_outro.data = posto_graduacao or ''
    form.is_rr.data = bool(getattr(instrutor, 'is_rr', False))


def _sync_user_with_payload(user: User, payload: dict) -> None:
    nome_completo = payload.get('nome_completo') or ''
    nome_de_guerra = payload.get('nome_de_guerra') or ''
    matricula = payload.get('matricula') or ''
    password = payload.get('password') or ''

    if nome_completo:
        user.nome_completo = nome_completo
    if nome_de_guerra:
        user.nome_de_guerra = nome_de_guerra
    if matricula:
        user.matricula = matricula
    if password:
        user.set_password(password)
    user.username = user.username or user.matricula
    user.role = user.role or 'instrutor'
    if user.role != 'instrutor':
        user.role = 'instrutor'


def _ensure_user_school_link(user_id: int, school_id: int) -> None:
    exists = db.session.scalar(
        select(UserSchool).where(
            UserSchool.user_id == user_id,
            UserSchool.school_id == school_id
        )
    )
    if not exists:
        us = UserSchool()
        us.user_id = user_id
        us.school_id = school_id
        us.role = 'instrutor'
        db.session.add(us)