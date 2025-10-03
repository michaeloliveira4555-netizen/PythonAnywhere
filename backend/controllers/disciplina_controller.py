# backend/controllers/disciplina_controller.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required
from sqlalchemy import select
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange

from ..models.database import db
from ..models.disciplina import Disciplina
from ..models.ciclo import Ciclo
from ..models.turma import Turma
from ..services.disciplina_service import DisciplinaService
from ..services.user_service import UserService
from utils.decorators import (
    admin_or_programmer_required,
    school_admin_or_programmer_required,
    can_view_management_pages_required
)

disciplina_bp = Blueprint('disciplina', __name__, url_prefix='/disciplina')


class DisciplinaForm(FlaskForm):
    materia = StringField('Matéria', validators=[DataRequired(), Length(min=3, max=100)])
    carga_horaria_prevista = IntegerField('Carga Horária Prevista', validators=[DataRequired(), NumberRange(min=1)])
    ciclo_id = SelectField('Ciclo', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Salvar')


class DeleteForm(FlaskForm):
    pass


@disciplina_bp.route('/')
@login_required
@can_view_management_pages_required
def listar_disciplinas():
    school_id = UserService.get_current_school_id()
    if not school_id:
        flash('Nenhuma escola associada ou selecionada.', 'warning')
        return redirect(url_for('main.dashboard'))

    ciclo_selecionado_id = request.args.get('ciclo', session.get('ultimo_ciclo_disciplina', 1), type=int)
    session['ultimo_ciclo_disciplina'] = ciclo_selecionado_id

    turma_selecionada_nome = request.args.get('turma', None)
    turmas_disponiveis = db.session.scalars(
        select(Turma).where(Turma.school_id == school_id).order_by(Turma.nome)
    ).all()

    query = select(Disciplina).where(
        Disciplina.school_id == school_id,
        Disciplina.ciclo_id == ciclo_selecionado_id
    ).order_by(Disciplina.materia)

    disciplinas = db.session.scalars(query).all()

    disciplinas_com_progresso = []
    for d in disciplinas:
        progresso = DisciplinaService.get_dados_progresso(d, turma_selecionada_nome)
        disciplinas_com_progresso.append({
            'disciplina': d,
            'progresso': progresso
        })

    delete_form = DeleteForm()
    ciclos_disponiveis = db.session.scalars(select(Ciclo).order_by(Ciclo.id)).all()

    return render_template('listar_disciplinas.html',
                           disciplinas_com_progresso=disciplinas_com_progresso,
                           delete_form=delete_form,
                           ciclo_selecionado=ciclo_selecionado_id,
                           ciclos=ciclos_disponiveis,
                           turmas=turmas_disponiveis,
                           turma_selecionada=turma_selecionada_nome)


@disciplina_bp.route('/adicionar', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required
def adicionar_disciplina():
    school_id = UserService.get_current_school_id()
    if not school_id:
        flash('Nenhuma escola associada ou selecionada.', 'danger')
        return redirect(url_for('disciplina.listar_disciplinas'))

    form = DisciplinaForm()
    ciclos = db.session.scalars(select(Ciclo).order_by(Ciclo.nome)).all()
    form.ciclo_id.choices = [(c.id, c.nome) for c in ciclos]

    if form.validate_on_submit():
        success, message = DisciplinaService.create_disciplina(form.data, school_id)
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('disciplina.listar_disciplinas'))
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('adicionar_disciplina.html', form=form)


@disciplina_bp.route('/editar/<int:disciplina_id>', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required
def editar_disciplina(disciplina_id):
    disciplina = db.session.get(Disciplina, disciplina_id)
    if not disciplina:
        flash('Disciplina não encontrada.', 'danger')
        return redirect(url_for('disciplina.listar_disciplinas'))

    form = DisciplinaForm(obj=disciplina)
    ciclos = db.session.scalars(select(Ciclo).order_by(Ciclo.nome)).all()
    form.ciclo_id.choices = [(c.id, c.nome) for c in ciclos]

    if form.validate_on_submit():
        success, message = DisciplinaService.update_disciplina(disciplina_id, form.data)
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('disciplina.listar_disciplinas'))

    return render_template('editar_disciplina.html', form=form, disciplina=disciplina)


@disciplina_bp.route('/excluir/<int:disciplina_id>', methods=['POST'])
@login_required
@school_admin_or_programmer_required
def excluir_disciplina(disciplina_id):
    form = DeleteForm()
    if form.validate_on_submit():
        success, message = DisciplinaService.delete_disciplina(disciplina_id)
        flash(message, 'success' if success else 'danger')
    else:
        flash('Falha na validação do token CSRF.', 'danger')

    return redirect(url_for('disciplina.listar_disciplinas'))


@disciplina_bp.route('/gerenciar-por-ciclo')
@login_required
@admin_or_programmer_required
def gerenciar_por_ciclo():
    school_id = UserService.get_current_school_id()
    if not school_id:
        flash('Nenhuma escola associada ou selecionada.', 'warning')
        return redirect(url_for('main.dashboard'))

    disciplinas_agrupadas = DisciplinaService.get_disciplinas_agrupadas_por_ciclo(school_id)
    delete_form = DeleteForm()

    return render_template('gerenciar_disciplinas_por_ciclo.html',
                           disciplinas_agrupadas=disciplinas_agrupadas,
                           delete_form=delete_form)


@disciplina_bp.route('/api/por-ciclo/<int:ciclo_id>')
@login_required
def api_disciplinas_por_ciclo(ciclo_id):
    school_id = UserService.get_current_school_id()
    if not school_id:
        return jsonify({'error': 'Escola não encontrada na sessão'}), 404

    disciplinas_query = (
        select(Disciplina)
        .where(Disciplina.school_id == school_id, Disciplina.ciclo_id == ciclo_id)
        .order_by(Disciplina.materia)
    )
    disciplinas = db.session.scalars(disciplinas_query).all()

    return jsonify([{'id': d.id, 'materia': d.materia} for d in disciplinas])
