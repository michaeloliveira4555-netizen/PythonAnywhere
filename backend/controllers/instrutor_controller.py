from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional, Email, Length

from backend.services.instrutor_service import InstrutorService
from utils.decorators import school_admin_or_programmer_required, can_view_management_pages_required
from backend.models.database import db
from backend.models.user import User
from backend.models.instrutor import Instrutor
from backend.models.school import School

instrutor_bp = Blueprint('instrutor', __name__, url_prefix='/instrutores')

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

class CadastroInstrutorForm(FlaskForm):
    nome_completo = StringField('Nome completo', validators=[Optional(), Length(max=255)])
    nome_de_guerra = StringField('Nome de guerra', validators=[Optional(), Length(max=255)])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(max=64)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=4)])
    posto_graduacao_select = SelectField('Posto/Graduação', choices=POSTOS_CHOICES)
    posto_graduacao_outro = StringField('Outro (especifique)', validators=[Optional(), Length(max=100)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=30)])
    is_rr = BooleanField('RR')
    submit = SubmitField('Salvar')

class EditarInstrutorForm(FlaskForm):
    nome_completo = StringField('Nome completo', validators=[Optional(), Length(max=255)])
    nome_de_guerra = StringField('Nome de guerra', validators=[Optional(), Length(max=255)])
    posto_graduacao_select = SelectField('Posto/Graduação', choices=POSTOS_CHOICES)
    posto_graduacao_outro = StringField('Outro (especifique)', validators=[Optional(), Length(max=100)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=30)])
    is_rr = BooleanField('RR')
    submit = SubmitField('Salvar')

def _resolve_school_id_for_user(user: User):
    if user and getattr(user, 'user_schools', None):
        for us in user.user_schools:
            return us.school_id
    sid = session.get('view_as_school_id')
    if sid:
        try:
            return int(sid)
        except Exception:
            pass
    return None

def _ensure_school_id_for_current_user(role_required: str = 'instrutor'):
    sid = _resolve_school_id_for_user(current_user)
    if sid:
        return sid
    ids = [row[0] for row in db.session.execute(db.select(School.id)).all()]
    return ids[0] if len(ids) == 1 else None

@instrutor_bp.route('/')
@login_required
@can_view_management_pages_required
def listar_instrutores():
    instrutores = InstrutorService.get_all_instrutores()
    form = DeleteForm()
    return render_template('listar_instrutores.html', instrutores=instrutores, form=form)

@instrutor_bp.route('/cadastrar', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required
def cadastrar_instrutor():
    form = CadastroInstrutorForm()
    if request.method == 'POST' and form.validate_on_submit():
        school_id = _ensure_school_id_for_current_user('instrutor')
        ok, msg = InstrutorService.create_full_instrutor(request.form.to_dict(flat=True), school_id)
        flash(msg, 'success' if ok else 'danger')
        if ok:
            return redirect(url_for('instrutor.listar_instrutores'))
    return render_template('cadastro_instrutor.html', form=form)

@instrutor_bp.route('/editar/<int:instrutor_id>', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required
def editar_instrutor(instrutor_id: int):
    instr = InstrutorService.get_instrutor_by_id(instrutor_id)
    if not instr:
        flash('Instrutor não encontrado.', 'danger')
        return redirect(url_for('instrutor.listar_instrutores'))
    form = EditarInstrutorForm()
    if request.method == 'POST' and form.validate_on_submit():
        ok, msg = InstrutorService.update_instrutor(instrutor_id, request.form.to_dict(flat=True))
        flash(msg, 'success' if ok else 'danger')
        if ok:
            return redirect(url_for('instrutor.listar_instrutores'))
    else:
        if instr and instr.user_id:
            user = db.session.get(User, instr.user_id)
            if user:
                form.nome_completo.data = user.nome_completo or ''
                form.nome_de_guerra.data = user.nome_de_guerra or ''
        form.telefone.data = instr.telefone or ''
        form.posto_graduacao_select.data = instr.posto_graduacao if instr.posto_graduacao in [c[0] for c in POSTOS_CHOICES] else 'Outro'
        form.posto_graduacao_outro.data = '' if form.posto_graduacao_select.data != 'Outro' else (instr.posto_graduacao or '')
        form.is_rr.data = bool(getattr(instr, 'is_rr', False))
    return render_template('editar_instrutor.html', form=form, instrutor=instr)

@instrutor_bp.route('/completar', methods=['GET', 'POST'])
@login_required
def completar_cadastro():
    form = EditarInstrutorForm()
    if request.method == 'POST' and form.validate_on_submit():
        instrutor_profile = current_user.instrutor_profile
        if not instrutor_profile:
            flash("Perfil de instrutor não encontrado para completar.", "danger")
            return redirect(url_for('main.dashboard'))
        
        ok, msg = InstrutorService.update_instrutor(instrutor_profile.id, request.form.to_dict(flat=True))
        flash(msg, 'success' if ok else 'danger')
        if ok:
            return redirect(url_for('main.dashboard'))
            
    return render_template('completar_cadastro_instrutor.html', form=form)


@instrutor_bp.route('/excluir/<int:instrutor_id>', methods=['POST'])
@login_required
@school_admin_or_programmer_required
def excluir_instrutor(instrutor_id: int):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Falha na validação do token CSRF.", "danger")
        return redirect(url_for('instrutor.listar_instrutores'))
    ok, msg = InstrutorService.delete_instrutor(instrutor_id)
    flash(msg, 'success' if ok else 'danger')
    return redirect(url_for('instrutor.listar_instrutores'))