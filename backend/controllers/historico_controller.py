# backend/controllers/historico_controller.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import StringField, TextAreaField, DateTimeLocalField, SubmitField, SelectField
from wtforms.validators import DataRequired

from ..models.database import db
from ..models.historico_disciplina import HistoricoDisciplina
from ..models.disciplina import Disciplina
from ..models.turma import Turma
from ..services.historico_service import HistoricoService
from ..services.aluno_service import AlunoService
from utils.decorators import admin_or_programmer_required, aluno_profile_required

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

# --- NOVAS ROTAS ADICIONADAS ---
@historico_bp.route('/')
@login_required
@aluno_profile_required
def index():
    """Página principal de seleção do 'Meu CTSP'."""
    return render_template('meu_ctsp_index.html')

@historico_bp.route('/sancoes')
@login_required
@aluno_profile_required
def sancoes():
    """Página para visualizar sanções (placeholder)."""
    return render_template('sancoes.html')

@historico_bp.route('/elogios')
@login_required
@aluno_profile_required
def elogios():
    """Página para visualizar elogios (placeholder)."""
    return render_template('elogios.html')

@historico_bp.route('/funcional')
@login_required
@aluno_profile_required
def historico_funcional():
    """Página para visualizar o histórico funcional (placeholder)."""
    return render_template('historico_funcional.html')
# --- FIM DAS NOVAS ROTAS ---

@historico_bp.route('/minhas-notas') # Rota antiga renomeada
@login_required
@aluno_profile_required
def minhas_notas():
    aluno_id = current_user.aluno_profile.id
    aluno = AlunoService.get_aluno_by_id(aluno_id)
    if not aluno:
        flash("Aluno não encontrado.", 'danger')
        return redirect(url_for('main.dashboard'))

    # Lógica de verificação e matrícula automática
    if aluno.turma and aluno.turma.school:
        school_id = aluno.turma.school.id
        disciplinas_da_escola = db.session.scalars(select(Disciplina).where(Disciplina.school_id == school_id)).all()
        matriculas_existentes = db.session.scalars(select(HistoricoDisciplina.disciplina_id).where(HistoricoDisciplina.aluno_id == aluno_id)).all()
        for disciplina in disciplinas_da_escola:
            if disciplina.id not in matriculas_existentes:
                nova_matricula = HistoricoDisciplina(aluno_id=aluno.id, disciplina_id=disciplina.id)
                db.session.add(nova_matricula)
        db.session.commit()

    historico_disciplinas = HistoricoService.get_historico_disciplinas_for_aluno(aluno_id)
    notas_finais = [h.nota for h in historico_disciplinas if h.nota is not None]
    media_final_curso = sum(notas_finais) / len(notas_finais) if notas_finais else 0.0

    return render_template('historico_aluno.html',
                           aluno=aluno,
                           historico_disciplinas=historico_disciplinas,
                           media_final_curso=media_final_curso,
                           is_own_profile=True)


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
    success, message, aluno_id = HistoricoService.avaliar_aluno(historico_id, form_data, from_admin=is_admin)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    # Redireciona de volta para a página de notas
    return redirect(url_for('historico.minhas_notas'))


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
    return redirect(url_for('historico.minhas_notas')) # Ajustar conforme a nova estrutura

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
    return redirect(url_for('historico.minhas_notas')) # Ajustar

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
    return redirect(url_for('historico.minhas_notas')) # Ajustar