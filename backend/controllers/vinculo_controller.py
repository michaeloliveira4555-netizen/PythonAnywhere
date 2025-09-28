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
from ..services.user_service import UserService 
from utils.decorators import admin_or_programmer_required, school_admin_or_programmer_required

vinculo_bp = Blueprint('vinculo', __name__, url_prefix='/vinculos')

# Forms
class VinculoForm(FlaskForm):
    instrutor_id = SelectField('Instrutor', coerce=int, validators=[DataRequired()])
    turma_id = SelectField('Turma', coerce=int, validators=[DataRequired()])
    disciplina_id = SelectField('Disciplina', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Salvar')

class DeleteForm(FlaskForm):
    pass

@vinculo_bp.route('/')
@login_required
@admin_or_programmer_required # Super Admin PODE ver
def gerenciar_vinculos():
    delete_form = DeleteForm()
    turma_filtrada = request.args.get('turma', '')
    disciplina_filtrada_id = request.args.get('disciplina_id', '')

    query = db.select(DisciplinaTurma).options(
        joinedload(DisciplinaTurma.instrutor_1).joinedload(Instrutor.user),
        joinedload(DisciplinaTurma.disciplina)
    ).filter(DisciplinaTurma.instrutor_id_1.isnot(None))

    if turma_filtrada:
        query = query.filter(DisciplinaTurma.pelotao == turma_filtrada)

    if disciplina_filtrada_id:
        query = query.filter(DisciplinaTurma.disciplina_id == int(disciplina_filtrada_id))

    query = query.order_by(DisciplinaTurma.pelotao, DisciplinaTurma.disciplina_id)
    vinculos = db.session.scalars(query).all()
    turmas = db.session.scalars(select(Turma).order_by(Turma.nome)).all()
    disciplinas = db.session.scalars(select(Disciplina).order_by(Disciplina.materia)).all()

    return render_template(
        'gerenciar_vinculos.html',
        vinculos=vinculos,
        turmas=turmas,
        disciplinas=disciplinas,
        turma_filtrada=turma_filtrada,
        disciplina_filtrada_id=int(disciplina_filtrada_id) if disciplina_filtrada_id else None,
        delete_form=delete_form
    )

@vinculo_bp.route('/adicionar', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required # Super Admin NÃO PODE adicionar
def adicionar_vinculo():
    form = VinculoForm()
    school_id = UserService.get_current_school_id()

    instrutores_query = select(Instrutor).join(User).order_by(User.nome_completo)
    instrutores = db.session.scalars(instrutores_query).all()
    
    turmas = []
    disciplinas = []
    if school_id:
        turmas = db.session.scalars(select(Turma).where(Turma.school_id == school_id).order_by(Turma.nome)).all()
        disciplinas = db.session.scalars(select(Disciplina).where(Disciplina.school_id == school_id).order_by(Disciplina.materia)).all()

    form.instrutor_id.choices = [(i.id, i.user.nome_completo) for i in instrutores]
    form.turma_id.choices = [(t.id, t.nome) for t in turmas]
    form.disciplina_id.choices = [(d.id, d.materia) for d in disciplinas]

    if form.validate_on_submit():
        turma = db.session.get(Turma, form.turma_id.data)
        vinculo_existente = db.session.execute(select(DisciplinaTurma).filter_by(disciplina_id=form.disciplina_id.data, pelotao=turma.nome)).scalar_one_or_none()

        if vinculo_existente:
            vinculo_existente.instrutor_id_1 = form.instrutor_id.data
            flash('Vínculo atualizado com sucesso!', 'info')
        else:
            novo_vinculo = DisciplinaTurma(
                instrutor_id_1=form.instrutor_id.data,
                pelotao=turma.nome,
                disciplina_id=form.disciplina_id.data
            )
            db.session.add(novo_vinculo)
            flash('Vínculo criado com sucesso!', 'success')
        
        db.session.commit()
        return redirect(url_for('vinculo.gerenciar_vinculos'))

    return render_template('adicionar_vinculo.html', form=form, turmas=turmas, disciplinas=disciplinas, instrutores=instrutores)


@vinculo_bp.route('/editar/<int:vinculo_id>', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required # Super Admin NÃO PODE editar
def editar_vinculo(vinculo_id):
    vinculo = db.session.get(DisciplinaTurma, vinculo_id)
    if not vinculo:
        flash('Vínculo não encontrado.', 'danger')
        return redirect(url_for('vinculo.gerenciar_vinculos'))

    form = VinculoForm(obj=vinculo)
    
    instrutores_query = select(Instrutor).join(User).order_by(User.nome_completo)
    instrutores = db.session.scalars(instrutores_query).all()
    turmas = db.session.scalars(select(Turma).order_by(Turma.nome)).all()
    disciplinas = db.session.scalars(select(Disciplina).order_by(Disciplina.materia)).all()
    
    form.instrutor_id.choices = [(i.id, i.user.nome_completo) for i in instrutores]
    form.turma_id.choices = [(t.id, t.nome) for t in turmas]
    form.disciplina_id.choices = [(d.id, d.materia) for d in disciplinas]

    if form.validate_on_submit():
        turma = db.session.get(Turma, form.turma_id.data)
        vinculo.instrutor_id_1 = form.instrutor_id.data
        vinculo.pelotao = turma.nome
        vinculo.disciplina_id = form.disciplina_id.data
        db.session.commit()
        flash('Vínculo atualizado com sucesso!', 'success')
        return redirect(url_for('vinculo.gerenciar_vinculos'))

    turma_atual = db.session.execute(select(Turma).filter_by(nome=vinculo.pelotao)).scalar_one_or_none()
    if turma_atual:
        form.turma_id.data = turma_atual.id
    form.instrutor_id.data = vinculo.instrutor_id_1
    form.disciplina_id.data = vinculo.disciplina_id

    return render_template('editar_vinculo.html', form=form, vinculo=vinculo)


@vinculo_bp.route('/excluir/<int:vinculo_id>', methods=['POST'])
@login_required
@school_admin_or_programmer_required # Super Admin NÃO PODE excluir
def excluir_vinculo(vinculo_id):
    form = DeleteForm()
    if form.validate_on_submit():
        vinculo = db.session.get(DisciplinaTurma, vinculo_id)
        if vinculo:
            db.session.delete(vinculo)
            db.session.commit()
            flash('Vínculo excluído com sucesso!', 'success')
        else:
            flash('Vínculo não encontrado.', 'danger')
    else:
        flash('Falha na validação do token CSRF.', 'danger')
    return redirect(url_for('vinculo.gerenciar_vinculos'))