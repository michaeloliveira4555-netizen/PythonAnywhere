# backend/controllers/vinculo_controller.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired

from ..models.database import db
from ..models.instrutor import Instrutor
from ..models.turma import Turma
from ..models.disciplina import Disciplina
from ..models.disciplina_turma import DisciplinaTurma
from ..models.user import User
from ..models.ciclo import Ciclo
from ..services.user_service import UserService 
from ..services.vinculo_service import VinculoService
from utils.decorators import admin_or_programmer_required, school_admin_or_programmer_required

vinculo_bp = Blueprint('vinculo', __name__, url_prefix='/vinculos')

class VinculoForm(FlaskForm):
    instrutor_id = SelectField('Instrutor', coerce=int, validators=[DataRequired()])
    turma_id = SelectField('Turma', coerce=int, validators=[DataRequired()])
    disciplina_id = SelectField('Disciplina', coerce=int, validators=[DataRequired(message="Por favor, selecione uma disciplina.")])
    submit = SubmitField('Salvar')

class DeleteForm(FlaskForm):
    pass

@vinculo_bp.route('/')
@login_required
@admin_or_programmer_required
def gerenciar_vinculos():
    turma_filtrada = request.args.get('turma', '')
    disciplina_filtrada_id = request.args.get('disciplina_id', type=int)
    
    school_id = UserService.get_current_school_id()
    if not school_id:
        flash("Nenhuma escola associada ou selecionada.", "warning")
        return redirect(url_for('main.dashboard'))

    vinculos = VinculoService.get_all_vinculos(turma_filtrada, disciplina_filtrada_id)
    turmas = db.session.scalars(select(Turma).where(Turma.school_id == school_id).order_by(Turma.nome)).all()
    disciplinas = db.session.scalars(select(Disciplina).where(Disciplina.school_id == school_id).order_by(Disciplina.materia)).all()
    delete_form = DeleteForm()
    
    return render_template('gerenciar_vinculos.html', 
                           vinculos=vinculos, 
                           turmas=turmas, 
                           disciplinas=disciplinas,
                           turma_filtrada=turma_filtrada,
                           disciplina_filtrada_id=disciplina_filtrada_id,
                           delete_form=delete_form)

@vinculo_bp.route('/adicionar', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required
def adicionar_vinculo():
    form = VinculoForm()
    school_id = UserService.get_current_school_id()
    
    # Prepara as opções para os menus dropdown
    instrutores = db.session.scalars(select(Instrutor).join(User).order_by(User.nome_completo)).all()
    turmas = db.session.scalars(select(Turma).where(Turma.school_id == school_id).order_by(Turma.nome)).all()
    ciclos = db.session.scalars(select(Ciclo).order_by(Ciclo.nome)).all()
    
    form.instrutor_id.choices = [(i.id, i.user.nome_completo or i.user.username) for i in instrutores]
    form.turma_id.choices = [(t.id, t.nome) for t in turmas]
    
    # CORREÇÃO: Popula as opções de disciplina no POST antes de validar
    if request.method == 'POST':
        disciplinas_do_school = db.session.scalars(select(Disciplina).where(Disciplina.school_id == school_id)).all()
        form.disciplina_id.choices = [(d.id, d.materia) for d in disciplinas_do_school]

    if form.validate_on_submit():
        success, message = VinculoService.add_vinculo(form.instrutor_id.data, form.turma_id.data, form.disciplina_id.data)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('vinculo.gerenciar_vinculos'))
    elif request.method == 'POST':
        # Mostra erros de validação ao utilizador
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{error}", 'danger')

    # Para o método GET, as disciplinas são carregadas por JS
    if request.method == 'GET':
        form.disciplina_id.choices = []

    return render_template('adicionar_vinculo.html', form=form, turmas=turmas, instrutores=instrutores, ciclos=ciclos)


@vinculo_bp.route('/editar/<int:vinculo_id>', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required
def editar_vinculo(vinculo_id):
    vinculo = db.session.get(DisciplinaTurma, vinculo_id)
    if not vinculo:
        flash("Vínculo não encontrado.", "danger")
        return redirect(url_for('vinculo.gerenciar_vinculos'))

    form = VinculoForm(obj=vinculo)
    school_id = UserService.get_current_school_id()
    
    instrutores = db.session.scalars(select(Instrutor).join(User).order_by(User.nome_completo)).all()
    turmas = db.session.scalars(select(Turma).where(Turma.school_id == school_id).order_by(Turma.nome)).all()
    disciplinas = db.session.scalars(select(Disciplina).where(Disciplina.school_id == school_id).order_by(Disciplina.materia)).all()

    form.instrutor_id.choices = [(i.id, i.user.nome_completo or i.user.username) for i in instrutores]
    form.turma_id.choices = [(t.id, t.nome) for t in turmas]
    form.disciplina_id.choices = [(d.id, d.materia) for d in disciplinas]
    
    if form.validate_on_submit():
        success, message = VinculoService.edit_vinculo(vinculo_id, form.instrutor_id.data, form.turma_id.data, form.disciplina_id.data)
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('vinculo.gerenciar_vinculos'))
    
    turma_atual = db.session.scalar(select(Turma).where(Turma.nome == vinculo.pelotao))
    if turma_atual:
        form.turma_id.data = turma_atual.id
    form.instrutor_id.data = vinculo.instrutor_id_1
    form.disciplina_id.data = vinculo.disciplina_id

    return render_template('editar_vinculo.html', form=form, vinculo=vinculo, turmas=turmas, disciplinas=disciplinas, instrutores=instrutores)

@vinculo_bp.route('/excluir/<int:vinculo_id>', methods=['POST'])
@login_required
@school_admin_or_programmer_required
def excluir_vinculo(vinculo_id):
    form = DeleteForm()
    if form.validate_on_submit():
        success, message = VinculoService.delete_vinculo(vinculo_id)
        flash(message, 'success' if success else 'danger')
    else:
        flash("Falha na validação do token CSRF.", "danger")
    return redirect(url_for('vinculo.gerenciar_vinculos'))