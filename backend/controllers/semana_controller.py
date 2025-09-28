# backend/controllers/semana_controller.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from sqlalchemy import select
from datetime import datetime, timedelta
import re
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField, SelectField
from wtforms.validators import DataRequired

from ..models.database import db
from ..models.semana import Semana
from ..models.horario import Horario
# Importa o novo modelo
from ..models.ciclo import Ciclo
from utils.decorators import admin_or_programmer_required
from ..services.semana_service import SemanaService

semana_bp = Blueprint('semana', __name__, url_prefix='/semana')

class AddSemanaForm(FlaskForm):
    nome = StringField('Nome da Semana', validators=[DataRequired()])
    data_inicio = DateField('Data de Início', validators=[DataRequired()])
    data_fim = DateField('Data de Fim', validators=[DataRequired()])
    ciclo_id = SelectField('Ciclo', coerce=int, validators=[DataRequired()])
    submit_add = SubmitField('Adicionar Semana')

class DeleteForm(FlaskForm):
    pass

@semana_bp.route('/gerenciar')
@login_required
@admin_or_programmer_required
def gerenciar_semanas():
    ciclo_selecionado_id = request.args.get('ciclo_id', type=int)
    
    todos_os_ciclos = db.session.scalars(select(Ciclo).order_by(Ciclo.nome)).all()

    if not ciclo_selecionado_id and todos_os_ciclos:
        ciclo_selecionado_id = todos_os_ciclos[0].id
    
    semanas = []
    if ciclo_selecionado_id:
        semanas = db.session.scalars(
            select(Semana).where(Semana.ciclo_id == ciclo_selecionado_id).order_by(Semana.data_inicio.desc())
        ).all()
    
    add_form = AddSemanaForm()
    add_form.ciclo_id.choices = [(c.id, c.nome) for c in todos_os_ciclos]
    
    delete_form = DeleteForm()
    
    return render_template('gerenciar_semanas.html', 
                           semanas=semanas, 
                           todos_os_ciclos=todos_os_ciclos, 
                           ciclo_selecionado_id=ciclo_selecionado_id,
                           add_form=add_form,
                           delete_form=delete_form)

# ... (o resto das funções, como adicionar_semana, editar_semana, etc. continuam iguais,
# mas precisam de ser ajustadas para usar ciclo_id em vez de ciclo)

# Rota para Adicionar Ciclo
@semana_bp.route('/ciclo/adicionar', methods=['POST'])
@login_required
@admin_or_programmer_required
def adicionar_ciclo():
    nome_ciclo = request.form.get('nome_ciclo')
    if nome_ciclo:
        if not db.session.scalar(select(Ciclo).where(Ciclo.nome == nome_ciclo)):
            db.session.add(Ciclo(nome=nome_ciclo))
            db.session.commit()
            flash(f"Ciclo '{nome_ciclo}' criado com sucesso!", "success")
        else:
            flash(f"Já existe um ciclo com o nome '{nome_ciclo}'.", "danger")
    else:
        flash("O nome do ciclo não pode estar vazio.", "danger")
    return redirect(url_for('semana.gerenciar_semanas'))


# Rota para Deletar Ciclo
@semana_bp.route('/ciclo/deletar/<int:ciclo_id>', methods=['POST'])
@login_required
@admin_or_programmer_required
def deletar_ciclo(ciclo_id):
    ciclo = db.session.get(Ciclo, ciclo_id)
    if ciclo:
        if ciclo.semanas or ciclo.disciplinas:
            flash("Não é possível deletar um ciclo que contém semanas ou disciplinas associadas.", "danger")
        else:
            db.session.delete(ciclo)
            db.session.commit()
            flash(f"Ciclo '{ciclo.nome}' deletado com sucesso.", "success")
    else:
        flash("Ciclo não encontrado.", "danger")
    return redirect(url_for('semana.gerenciar_semanas'))