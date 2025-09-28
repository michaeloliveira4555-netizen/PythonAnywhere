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
# Importa o novo modelo
from ..models.ciclo import Ciclo
from ..services.user_service import UserService 
from utils.decorators import admin_or_programmer_required, school_admin_or_programmer_required

vinculo_bp = Blueprint('vinculo', __name__, url_prefix='/vinculos')

# ... (código dos formulários permanece igual)

@vinculo_bp.route('/adicionar', methods=['GET', 'POST'])
@login_required
@school_admin_or_programmer_required
def adicionar_vinculo():
    form = VinculoForm()
    school_id = UserService.get_current_school_id()
    
    # Busca os ciclos dinamicamente
    ciclos = db.session.scalars(select(Ciclo).order_by(Ciclo.nome)).all()

    # ... (resto da função permanece igual, mas agora passamos os ciclos para o template)
    
    return render_template('adicionar_vinculo.html', form=form, turmas=turmas, disciplinas=disciplinas, instrutores=instrutores, ciclos=ciclos)