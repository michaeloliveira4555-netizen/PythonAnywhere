# backend/controllers/historico_controller.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeLocalField, SubmitField, SelectField
from wtforms.validators import DataRequired

from ..models.database import db
from ..models.historico_disciplina import HistoricoDisciplina
from ..services.historico_service import HistoricoService
from ..services.aluno_service import AlunoService
from utils.decorators import admin_or_programmer_required

historico_bp = Blueprint('historico', __name__, url_prefix='/historico')

# Formulário para adicionar/editar atividades
class AtividadeForm(FlaskForm):
    tipo = SelectField('Tipo de Atividade', choices=[
        ('Elogio', 'Elogio'),
        ('Sanção Disciplinar', 'Sanção Disciplinar'),
        ('Observação', 'Observação'),
        ('Atualização Cadastral', 'Atualização Cadastral'),
        ('Outro', 'Outro')
    ], validators=[DataRequired()])
    descricao = TextAreaField('Descrição', validators=[DataRequired()])
    data_inicio = DateTimeLocalField('Data e Hora do Evento', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    submit = SubmitField('Salvar Atividade')

class DeleteForm(FlaskForm):
    pass # Apenas para o token CSRF

@historico_bp.route('/aluno/<int:aluno_id>')
@login_required
def historico_aluno(aluno_id):
    user_role = getattr(current_user, 'role', None)
    is_admin = user_role in ['super_admin', 'programador', 'admin_escola']
    is_own_profile = hasattr(current_user, 'aluno_profile') and current_user.aluno_profile and current_user.aluno_profile.id == aluno_id

    if not (is_admin or is_own_profile):
        flash("Você não tem permissão para visualizar este histórico.", 'danger')
        return redirect(url_for('main.dashboard'))

    aluno = AlunoService.get_aluno_by_id(aluno_id)
    if not aluno:
        flash("Aluno não encontrado.", 'danger')
        return redirect(url_for('main.dashboard'))

    historico_disciplinas = HistoricoService.get_historico_disciplinas_for_aluno(aluno_id)
    historico_atividades = HistoricoService.get_historico_atividades_for_aluno(aluno_id)
    
    notas_finais = [h.nota for h in historico_disciplinas if h.nota is not None]
    media_final_curso = sum(notas_finais) / len(notas_finais) if notas_finais else 0.0

    form = AtividadeForm()
    delete_form = DeleteForm()

    return render_template('historico_aluno.html',
                           aluno=aluno,
                           historico_disciplinas=historico_disciplinas,
                           historico_atividades=historico_atividades,
                           media_final_curso=media_final_curso,
                           form=form,
                           delete_form=delete_form,
                           is_own_profile=is_own_profile) # Passa a flag para o template


@historico_bp.route('/avaliar/<int:historico_id>', methods=['POST'])
@login_required
def avaliar_aluno_disciplina(historico_id):
    registro = db.session.get(HistoricoDisciplina, historico_id)
    if not registro:
        flash("Registro de avaliação não encontrado.", 'danger')
        return redirect(url_for('main.dashboard'))

    is_own_profile = hasattr(current_user, 'aluno_profile') and current_user.aluno_profile.id == registro.aluno_id
    is_admin = getattr(current_user, 'role', None) in ['super_admin', 'programador', 'admin_escola']

    if not (is_own_profile or is_admin):
        flash("Você não tem permissão para realizar esta ação.", 'danger')
        return redirect(url_for('main.dashboard'))

    form_data = request.form.to_dict()
    # Passa a flag 'from_admin' para o serviço
    success, message, aluno_id = HistoricoService.avaliar_aluno(historico_id, form_data, from_admin=is_admin)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    if aluno_id:
        return redirect(url_for('historico.historico_aluno', aluno_id=aluno_id))
    else:
        return redirect(url_for('main.dashboard'))

# --- ROTAS CORRIGIDAS E ADICIONADAS ---

@historico_bp.route('/atividade/adicionar/<int:aluno_id>', methods=['POST'])
@login_required
@admin_or_programmer_required
def adicionar_atividade(aluno_id):
    form = AtividadeForm()
    if form.validate_on_submit():
        success, message = HistoricoService.add_atividade_aluno(aluno_id, form.data)
        flash(message, 'success' if success else 'danger')
    else:
        flash('Erro de validação no formulário.', 'danger')
    return redirect(url_for('historico.historico_aluno', aluno_id=aluno_id))

@historico_bp.route('/atividade/editar/<int:atividade_id>', methods=['POST'])
@login_required
@admin_or_programmer_required
def editar_atividade(atividade_id):
    form = AtividadeForm()
    aluno_id = request.form.get('aluno_id')
    if form.validate_on_submit():
        success, message = HistoricoService.update_atividade_aluno(atividade_id, form.data)
        flash(message, 'success' if success else 'danger')
    else:
        flash('Erro de validação no formulário.', 'danger')
    return redirect(url_for('historico.historico_aluno', aluno_id=aluno_id))

@historico_bp.route('/atividade/deletar/<int:atividade_id>', methods=['POST'])
@login_required
@admin_or_programmer_required
def deletar_atividade(atividade_id):
    aluno_id = request.form.get('aluno_id')
    delete_form = DeleteForm()
    if delete_form.validate_on_submit():
        success, message = HistoricoService.delete_atividade_aluno(atividade_id)
        flash(message, 'success' if success else 'danger')
    else:
        flash('Falha na validação do token CSRF.', 'danger')
    return redirect(url_for('historico.historico_aluno', aluno_id=aluno_id))