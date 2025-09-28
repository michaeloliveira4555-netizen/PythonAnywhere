# backend/controllers/semana_controller.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from sqlalchemy import select
from datetime import datetime, timedelta
import re
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField
from wtforms.validators import DataRequired

from ..models.database import db
from ..models.semana import Semana
from ..models.horario import Horario
from utils.decorators import admin_or_programmer_required
from ..services.semana_service import SemanaService

semana_bp = Blueprint('semana', __name__, url_prefix='/semana')

# Formulários
class AddSemanaForm(FlaskForm):
    nome = StringField('Nome da Semana', validators=[DataRequired()])
    data_inicio = DateField('Data de Início', validators=[DataRequired()])
    data_fim = DateField('Data de Fim', validators=[DataRequired()])
    submit_add = SubmitField('Adicionar Semana')

class DeleteSemanaForm(FlaskForm):
    pass # Apenas para o token CSRF

@semana_bp.route('/gerenciar')
@login_required
@admin_or_programmer_required
def gerenciar_semanas():
    ciclo_selecionado = request.args.get('ciclo', session.get('ultimo_ciclo_semana', 1), type=int)
    session['ultimo_ciclo_semana'] = ciclo_selecionado
    
    semanas = db.session.scalars(
        select(Semana).where(Semana.ciclo == ciclo_selecionado).order_by(Semana.data_inicio.desc())
    ).all()
    
    # --- CORREÇÃO APLICADA AQUI ---
    add_form = AddSemanaForm()
    delete_form = DeleteSemanaForm()
    
    return render_template('gerenciar_semanas.html', 
                           semanas=semanas, 
                           ciclos=[1, 2, 3], 
                           ciclo_selecionado=ciclo_selecionado,
                           add_form=add_form,
                           delete_form=delete_form)

@semana_bp.route('/adicionar', methods=['POST'])
@login_required
@admin_or_programmer_required
def adicionar_semana():
    ciclo = request.form.get('ciclo', 1, type=int)
    try:
        nome = request.form.get('nome')
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')

        if not all([nome, data_inicio_str, data_fim_str]):
            flash('Todos os campos são obrigatórios.', 'danger')
            return redirect(url_for('semana.gerenciar_semanas', ciclo=ciclo))

        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()

        nova_semana = Semana(nome=nome, data_inicio=data_inicio, data_fim=data_fim, ciclo=ciclo)
        
        nova_semana.mostrar_periodo_13 = 'mostrar_periodo_13' in request.form
        nova_semana.mostrar_periodo_14 = 'mostrar_periodo_14' in request.form
        nova_semana.mostrar_periodo_15 = 'mostrar_periodo_15' in request.form
        nova_semana.mostrar_sabado = 'mostrar_sabado' in request.form
        nova_semana.periodos_sabado = int(request.form.get('periodos_sabado', 0)) if nova_semana.mostrar_sabado else 0
        nova_semana.mostrar_domingo = 'mostrar_domingo' in request.form
        nova_semana.periodos_domingo = int(request.form.get('periodos_domingo', 0)) if nova_semana.mostrar_domingo else 0

        db.session.add(nova_semana)
        db.session.commit()
        
        flash('Nova semana cadastrada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao adicionar semana: {e}', 'danger')
        db.session.rollback()

    return redirect(url_for('semana.gerenciar_semanas', ciclo=ciclo))

@semana_bp.route('/adicionar-proxima', methods=['POST'])
@login_required
@admin_or_programmer_required
def adicionar_proxima_semana():
    ciclo = request.form.get('ciclo', 1, type=int)
    ultima_semana = db.session.scalars(
        select(Semana).where(Semana.ciclo == ciclo).order_by(Semana.data_fim.desc())
    ).first()

    if not ultima_semana:
        flash(f'Para adicionar a "próxima semana", cadastre a primeira semana do Ciclo {ciclo} manualmente.', 'warning')
        return redirect(url_for('semana.gerenciar_semanas', ciclo=ciclo))

    numeros = re.findall(r'\d+', ultima_semana.nome)
    proximo_numero = int(numeros[-1]) + 1 if numeros else 1
    novo_nome = f"Semana {proximo_numero}"

    dias_para_proxima_segunda = (7 - ultima_semana.data_fim.weekday()) % 7
    if dias_para_proxima_segunda == 0:
        dias_para_proxima_segunda = 1
        
    nova_data_inicio = ultima_semana.data_fim + timedelta(days=dias_para_proxima_segunda)
    nova_data_fim = nova_data_inicio + timedelta(days=4)

    nova_semana = Semana(
        nome=novo_nome, data_inicio=nova_data_inicio, data_fim=nova_data_fim, ciclo=ciclo,
        mostrar_periodo_13=False, mostrar_periodo_14=False, mostrar_periodo_15=False,
        mostrar_sabado=False, periodos_sabado=0,
        mostrar_domingo=False, periodos_domingo=0
    )
    db.session.add(nova_semana)
    db.session.commit()

    flash(f'"{novo_nome}" adicionada com sucesso ao Ciclo {ciclo}!', 'success')
    return redirect(url_for('semana.gerenciar_semanas', ciclo=ciclo))

@semana_bp.route('/editar/<int:semana_id>', methods=['GET', 'POST'])
@login_required
@admin_or_programmer_required
def editar_semana(semana_id):
    semana = SemanaService.get_semana_by_id(semana_id)
    if not semana:
        flash('Semana não encontrada.', 'danger')
        return redirect(url_for('semana.gerenciar_semanas'))

    if request.method == 'POST':
        try:
            semana.nome = request.form.get('nome')
            semana.data_inicio = datetime.strptime(request.form.get('data_inicio'), '%Y-%m-%d').date()
            semana.data_fim = datetime.strptime(request.form.get('data_fim'), '%Y-%m-%d').date()
            
            semana.mostrar_periodo_13 = 'mostrar_periodo_13' in request.form
            semana.mostrar_periodo_14 = 'mostrar_periodo_14' in request.form
            semana.mostrar_periodo_15 = 'mostrar_periodo_15' in request.form
            semana.mostrar_sabado = 'mostrar_sabado' in request.form
            semana.periodos_sabado = int(request.form.get('periodos_sabado', 0)) if semana.mostrar_sabado else 0
            semana.mostrar_domingo = 'mostrar_domingo' in request.form
            semana.periodos_domingo = int(request.form.get('periodos_domingo', 0)) if semana.mostrar_domingo else 0

            db.session.commit()
            flash('Semana atualizada com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao atualizar semana: {e}', 'danger')
            db.session.rollback()

        return redirect(url_for('semana.gerenciar_semanas', ciclo=semana.ciclo))

    
    return render_template('editar_semana.html', semana=semana)


@semana_bp.route('/deletar/<int:semana_id>', methods=['POST'])
@login_required
@admin_or_programmer_required
def deletar_semana(semana_id):
    semana = db.session.get(Semana, semana_id)
    if semana:
        ciclo_redirect = semana.ciclo
        db.session.query(Horario).filter_by(semana_id=semana_id).delete()
        db.session.delete(semana)
        db.session.commit()
        flash('Semana e todas as suas aulas foram deletadas com sucesso.', 'success')
        return redirect(url_for('semana.gerenciar_semanas', ciclo=ciclo_redirect))
    else:
        flash('Semana não encontrada.', 'danger')
        return redirect(url_for('semana.gerenciar_semanas'))