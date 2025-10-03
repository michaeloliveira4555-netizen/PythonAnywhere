# backend/controllers/aluno_controller.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from sqlalchemy import select
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional

from ..models.database import db
from ..services.aluno_service import AlunoService
from ..models.user import User
from ..models.aluno import Aluno  # noqa: F401
from ..models.turma import Turma
from utils.decorators import admin_or_programmer_required, school_admin_or_programmer_required, can_view_management_pages_required  # noqa: F401

aluno_bp = Blueprint('aluno', __name__, url_prefix='/aluno')

class AlunoProfileForm(FlaskForm):
    foto_perfil = FileField('Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    nome_completo = StringField('Nome Completo', validators=[DataRequired()])
    opm = StringField('OPM', validators=[DataRequired()])
    turma_id = SelectField('Turma / Pelotão', coerce=int, validators=[Optional()])
    submit = SubmitField('Salvar Perfil')

class DeleteForm(FlaskForm):
    pass

def _resolve_school_id_for_user(user: User):
    if user and getattr(user, 'user_schools', None):
        for us in user.user_schools:
            return us.school_id
    return None

def _ensure_school_id_for_current_user(role_required: str = "aluno"):
    from ..models.school import School
    from ..models.user_school import UserSchool
    sid = _resolve_school_id_for_user(current_user)
    if sid:
        return sid
    sid = session.get('view_as_school_id')
    if sid:
        return int(sid)
    ids = [row[0] for row in db.session.execute(db.select(School.id)).all()]
    if len(ids) == 1:
        only_id = ids[0]
        exists = db.session.execute(
            db.select(UserSchool.id).filter_by(user_id=current_user.id, school_id=only_id)
        ).scalar()
        if not exists:
            from ..services.user_service import UserService
            ok, _ = UserService.assign_school_role(current_user.id, only_id, role_required)
            if not ok:
                db.session.add(UserSchool(user_id=current_user.id, school_id=only_id, role=role_required))
                db.session.commit()
        return only_id
    return None

class EditAlunoForm(FlaskForm):
    foto_perfil = FileField('Alterar Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    nome_completo = StringField('Nome Completo', validators=[DataRequired()])
    matricula = StringField('Matrícula', validators=[DataRequired()])
    opm = StringField('OPM', validators=[DataRequired()])
    turma_id = SelectField('Turma / Pelotão', coerce=int, validators=[DataRequired()])
    funcao_atual = SelectField('Função Atual', choices=[
        ('', '-- Nenhuma função --'), ('P1', 'P1'), ('P2', 'P2'), ('P3', 'P3'), ('P4', 'P4'), ('P5', 'P5'),
        ('Aux Disc', 'Aux Disc'), ('Aux Cia', 'Aux Cia'), ('Aux Pel', 'Aux Pel'), ('C1', 'C1'), ('C2', 'C2'),
        ('C3', 'C3'), ('C4', 'C4'), ('C5', 'C5'), ('Formatura', 'Formatura'), ('Obras', 'Obras'),
        ('Atletismo', 'Atletismo'), ('Jubileu', 'Jubileu'), ('Dia da Criança', 'Dia da Criança'),
        ('Seminário', 'Seminário'), ('Chefe de Turma', 'Chefe de Turma'), ('Correio', 'Correio'),
        ('Cmt 1° GPM', 'Cmt 1° GPM'), ('Cmt 2° GPM', 'Cmt 2° GPM'), ('Cmt 3° GPM', 'Cmt 3° GPM'),
        ('Socorrista 1', 'Socorrista 1'), ('Socorrista 2', 'Socorrista 2'), ('Motorista 1', 'Motorista 1'),
        ('Motorista 2', 'Motorista 2'), ('Telefonista 1', 'Telefonista 1'), ('Telefonista 2', 'Telefonista 2')
    ], validators=[Optional()])
    submit = SubmitField('Atualizar Perfil')

# --- ROTA 'completar_cadastro' REMOVIDA DAQUI ---

@aluno_bp.route('/listar')
@login_required
@can_view_management_pages_required
def listar_alunos():
    delete_form = DeleteForm()
    turma_filtrada = request.args.get('turma', None)
    
    school_id = _ensure_school_id_for_current_user()
    if not school_id:
        flash('Nenhuma escola associada ou selecionada.', 'danger')
        return redirect(url_for('main.dashboard'))

    alunos = AlunoService.get_all_alunos(current_user, turma_filtrada)
    turmas = db.session.scalars(select(Turma).where(Turma.school_id==school_id).order_by(Turma.nome)).all()
    return render_template('listar_alunos.html', alunos=alunos, turmas=turmas, turma_filtrada=turma_filtrada, delete_form=delete_form)

@aluno_bp.route('/editar/<int:aluno_id>', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required
def editar_aluno(aluno_id):
    aluno = AlunoService.get_aluno_by_id(aluno_id)
    if not aluno:
        flash("Aluno não encontrado.", 'danger')
        return redirect(url_for('aluno.listar_alunos'))

    school_id = _ensure_school_id_for_current_user()
    if not school_id:
        flash('Nenhuma escola associada ou selecionada.', 'danger')
        return redirect(url_for('aluno.listar_alunos'))

    form = EditAlunoForm(obj=aluno)
    turmas = db.session.scalars(select(Turma).where(Turma.school_id==school_id).order_by(Turma.nome)).all()
    form.turma_id.choices = [(t.id, t.nome) for t in turmas]

    if request.method == 'GET':
        if aluno.user:
            form.nome_completo.data = aluno.user.nome_completo
            form.matricula.data = aluno.user.matricula
        form.opm.data = aluno.opm
        form.turma_id.data = aluno.turma_id
        form.funcao_atual.data = aluno.funcao_atual

    if form.validate_on_submit():
        form_data = form.data
        foto_perfil = form.foto_perfil.data

        success, message = AlunoService.update_aluno(aluno_id, form_data, foto_perfil)
        if success:
            flash(message, 'success')
            return redirect(url_for('aluno.listar_alunos'))
        else:
            flash(message, 'error')

    return render_template('editar_aluno.html', aluno=aluno, form=form, turmas=turmas, self_edit=False)


@aluno_bp.route('/excluir/<int:aluno_id>', methods=['POST'])
@login_required
@school_admin_or_programmer_required
def excluir_aluno(aluno_id):
    form = DeleteForm()
    if form.validate_on_submit():
        success, message = AlunoService.delete_aluno(aluno_id)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    else:
        flash('Falha na validação do token CSRF.', 'danger')
    return redirect(url_for('aluno.listar_alunos'))