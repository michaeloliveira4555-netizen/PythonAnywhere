# backend/services/horario_service.py

from flask import current_app
from flask_login import current_user
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from datetime import date, timedelta

from ..models.database import db
from ..models.horario import Horario
from ..models.disciplina import Disciplina
from ..models.instrutor import Instrutor
from ..models.disciplina_turma import DisciplinaTurma
from ..models.semana import Semana
from ..models.turma import Turma
from ..models.user import User


class HorarioService:

    @staticmethod
    def can_edit_horario(horario, user):
        """Verifica se um usuário pode editar um horário específico."""
        if not horario or not user:
            return False
        if user.role in ['super_admin', 'programador', 'admin_escola']:
            return True
        if user.role == 'instrutor' and user.instrutor_profile:
            return horario.instrutor_id == user.instrutor_profile.id
        return False

    @staticmethod
    def construir_matriz_horario(pelotao, semana_id, user):
        """Constrói a matriz 15x7 para exibir o quadro de horários, pulando os intervalos."""
        a_disposicao = {'materia': 'A disposição do C Al /S Ens', 'instrutor': None, 'duracao': 1, 'is_disposicao': True, 'id': None, 'status': 'confirmado'}
        horario_matrix = [[dict(a_disposicao) for _ in range(7)] for _ in range(15)]
        dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo']
        
        aulas = db.session.scalars(
            select(Horario).options(
                joinedload(Horario.disciplina),
                joinedload(Horario.instrutor).joinedload(Instrutor.user)
            ).where(Horario.pelotao == pelotao, Horario.semana_id == semana_id)
        ).all()

        for aula in aulas:
            try:
                dia_idx = dias.index(aula.dia_semana)
                
                periodos_processados = 0
                periodo_inicial_bloco = aula.periodo
                is_continuation = False

                while periodos_processados < aula.duracao:
                    periodo_atual_idx = periodo_inicial_bloco - 1
                    periodos_restantes = aula.duracao - periodos_processados

                    duracao_bloco = 0
                    if periodo_inicial_bloco <= 3:
                        max_periodos_neste_bloco = 3 - periodo_inicial_bloco + 1
                        duracao_bloco = min(periodos_restantes, max_periodos_neste_bloco)
                    elif periodo_inicial_bloco <= 9:
                        max_periodos_neste_bloco = 9 - periodo_inicial_bloco + 1
                        duracao_bloco = min(periodos_restantes, max_periodos_neste_bloco)
                    else:
                        duracao_bloco = periodos_restantes
                    
                    if duracao_bloco <= 0:
                        break

                    can_see_details = HorarioService.can_edit_horario(aula, user)
                    instrutor_nome = "N/D"
                    if aula.instrutor and aula.instrutor.user:
                        instrutor_nome = aula.instrutor.user.nome_de_guerra or aula.instrutor.user.username

                    aula_info = {
                        'id': aula.id,
                        'materia': aula.disciplina.materia if aula.status == 'confirmado' or can_see_details else 'Aguardando Aprovação',
                        'instrutor': instrutor_nome if aula.status == 'confirmado' or can_see_details else None,
                        'observacao': aula.observacao, # --- CAMPO NOVO ADICIONADO ---
                        'duracao': duracao_bloco,
                        'status': aula.status,
                        'is_disposicao': False,
                        'can_edit': can_see_details,
                        'is_continuation': is_continuation
                    }
                    
                    if 0 <= periodo_atual_idx < 15:
                        horario_matrix[periodo_atual_idx][dia_idx] = aula_info
                        for i in range(1, duracao_bloco):
                            if (periodo_atual_idx + i) < 15:
                                horario_matrix[periodo_atual_idx + i][dia_idx] = 'SKIP'

                    periodos_processados += duracao_bloco
                    periodo_inicial_bloco += duracao_bloco
                    is_continuation = True

            except (ValueError, IndexError):
                continue
        return horario_matrix

    @staticmethod
    def get_semana_selecionada(semana_id_str, ciclo_id):
        # ... (código existente sem alterações)
        if semana_id_str and semana_id_str.isdigit():
            return db.session.get(Semana, int(semana_id_str))
        
        today = date.today()
        semana_atual = db.session.scalars(
            select(Semana).where(
                Semana.ciclo_id == ciclo_id,
                Semana.data_inicio <= today,
                Semana.data_fim >= today
            )
        ).first()
        if semana_atual:
            return semana_atual
            
        return db.session.scalars(
            select(Semana).where(Semana.ciclo_id == ciclo_id).order_by(Semana.data_inicio.desc())
        ).first()

    @staticmethod
    def get_datas_da_semana(semana):
        # ... (código existente sem alterações)
        if not semana:
            return {}
        datas = {}
        dias = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo']
        for i, dia_nome in enumerate(dias):
            data_calculada = semana.data_inicio + timedelta(days=i)
            datas[dia_nome] = data_calculada.strftime('%d/%m')
        return datas

    @staticmethod
    def get_edit_grid_context(pelotao, semana_id, ciclo_id, user):
        # ... (código existente sem alterações)
        horario_matrix = HorarioService.construir_matriz_horario(pelotao, semana_id, user)
        semana = db.session.get(Semana, semana_id)
        is_admin = user.role in ['super_admin', 'programador', 'admin_escola']
        
        def get_horas_agendadas(disciplina_id, pelotao_nome):
            total_agendado = db.session.scalar(
                select(func.sum(Horario.duracao)).where(
                    Horario.disciplina_id == disciplina_id,
                    Horario.pelotao == pelotao_nome
                )
            )
            return total_agendado or 0

        disciplinas_disponiveis = []
        if is_admin:
            disciplinas_do_ciclo = db.session.scalars(select(Disciplina).where(Disciplina.ciclo_id == ciclo_id).order_by(Disciplina.materia)).all()
            for d in disciplinas_do_ciclo:
                horas_agendadas = get_horas_agendadas(d.id, pelotao)
                horas_restantes = d.carga_horaria_prevista - horas_agendadas
                disciplinas_disponiveis.append({"id": d.id, "nome": d.materia, "restantes": horas_restantes})
        else:
            instrutor_id = user.instrutor_profile.id if user.instrutor_profile else 0
            disciplinas_do_instrutor = db.session.scalars(
                select(Disciplina)
                .join(DisciplinaTurma, Disciplina.id == DisciplinaTurma.disciplina_id)
                .where(
                    DisciplinaTurma.pelotao == pelotao,
                    Disciplina.ciclo_id == ciclo_id,
                    (DisciplinaTurma.instrutor_id_1 == instrutor_id) | (DisciplinaTurma.instrutor_id_2 == instrutor_id)
                )
                .order_by(Disciplina.materia)
            ).all()

            for d in disciplinas_do_instrutor:
                horas_agendadas = get_horas_agendadas(d.id, pelotao)
                horas_restantes = d.carga_horaria_prevista - horas_agendadas
                disciplinas_disponiveis.append({"id": d.id, "nome": d.materia, "restantes": horas_restantes})

        todos_instrutores = [{"id": i.id, "nome": i.user.nome_de_guerra or i.user.username} for i in db.session.scalars(select(Instrutor).options(joinedload(Instrutor.user)).join(User).order_by(User.nome_de_guerra)).all()]

        return {
            'success': True,
            'horario_matrix': horario_matrix,
            'pelotao_selecionado': pelotao,
            'semana_selecionada': semana,
            'disciplinas_disponiveis': disciplinas_disponiveis,
            'todos_instrutores': todos_instrutores,
            'is_admin': is_admin,
            'instrutor_logado_id': user.instrutor_profile.id if user.instrutor_profile else None,
            'datas_semana': HorarioService.get_datas_da_semana(semana)
        }

    @staticmethod
    def get_aula_details(horario_id, user):
        """Busca os detalhes de uma aula para o modal de edição."""
        aula = db.session.get(Horario, horario_id)
        if not aula or not HorarioService.can_edit_horario(aula, user):
            return None
        return {
            'disciplina_id': aula.disciplina_id,
            'instrutor_id': aula.instrutor_id,
            'duracao': aula.duracao,
            'observacao': aula.observacao # --- CAMPO NOVO ADICIONADO ---
        }

    @staticmethod
    def save_aula(data, user):
        """Salva uma nova aula ou atualiza uma existente."""
        try:
            horario_id = data.get('horario_id')
            pelotao = data['pelotao']
            semana_id = int(data['semana_id'])
            dia = data['dia']
            periodo = int(data['periodo'])
            disciplina_id = int(data['disciplina_id'])
            duracao = int(data.get('duracao', 1))
            observacao = data.get('observacao', '').strip() or None # --- CAMPO NOVO ADICIONADO ---
            is_admin = user.role in ['super_admin', 'programador', 'admin_escola']
            
            disciplina = db.session.get(Disciplina, disciplina_id)
            if not disciplina:
                return False, 'Disciplina não encontrada.', 404
                
            total_agendado = db.session.scalar(
                select(func.sum(Horario.duracao)).where(
                    Horario.disciplina_id == disciplina_id,
                    Horario.pelotao == pelotao,
                    Horario.id != horario_id
                )
            ) or 0
            
            horas_restantes = disciplina.carga_horaria_prevista - total_agendado
            if duracao > horas_restantes:
                return False, f'Não é possível agendar {duracao}h. Apenas {horas_restantes}h restam para esta disciplina.', 400

            instrutor_id = None
            if is_admin:
                instrutor_id_from_form = data.get('instrutor_id')
                if not instrutor_id_from_form:
                    return False, 'Como administrador, você deve selecionar um instrutor.', 400
                instrutor_id = int(instrutor_id_from_form)
            else:
                if not user.instrutor_profile:
                    return False, 'O seu perfil de instrutor não foi encontrado.', 403
                instrutor_id = user.instrutor_profile.id

            if not instrutor_id:
                return False, 'Instrutor não especificado.', 400

        except (KeyError, ValueError, TypeError):
            return False, 'Dados inválidos ou incompletos.', 400

        if horario_id:
            aula = db.session.get(Horario, int(horario_id))
            if not aula:
                return False, 'Aula não encontrada.', 404
            if not HorarioService.can_edit_horario(aula, user):
                return False, 'Sem permissão para editar esta aula.', 403
        else:
            conflito = db.session.execute(
                select(Horario).where(
                    Horario.pelotao == pelotao,
                    Horario.semana_id == semana_id,
                    Horario.dia_semana == dia,
                    Horario.periodo == periodo,
                )
            ).scalar_one_or_none()
            if conflito:
                return False, 'Já existe uma aula neste horário.', 409
            aula = Horario(status='confirmado' if is_admin else 'pendente')
            db.session.add(aula)
        
        # --- ATUALIZAÇÃO PARA INCLUIR OBSERVAÇÃO ---
        aula.pelotao, aula.semana_id, aula.dia_semana, aula.periodo, aula.disciplina_id, aula.duracao, aula.instrutor_id, aula.observacao = \
            pelotao, semana_id, dia, periodo, disciplina_id, duracao, instrutor_id, observacao

        try:
            db.session.commit()
            return True, 'Aula salva com sucesso!', 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao salvar aula: {e}")
            return False, 'Erro interno do servidor ao salvar.', 500
            
    @staticmethod
    def remove_aula(horario_id, user):
        # ... (código existente sem alterações)
        aula = db.session.get(Horario, int(horario_id))
        if not aula:
            return False, 'Aula não encontrada.'
        if not HorarioService.can_edit_horario(aula, user):
            return False, 'Sem permissão para remover esta aula.'
        
        db.session.delete(aula)
        db.session.commit()
        return True, 'Aula removida com sucesso!'

    @staticmethod
    def get_aulas_pendentes():
        # ... (código existente sem alterações)
        return db.session.scalars(
            select(Horario).options(
                joinedload(Horario.disciplina),
                joinedload(Horario.instrutor).joinedload(Instrutor.user),
                joinedload(Horario.semana)
            ).where(Horario.status == 'pendente').order_by(Horario.id.desc())
        ).all()
        
    @staticmethod
    def aprovar_horario(horario_id, action):
        # ... (código existente sem alterações)
        aula = db.session.get(Horario, int(horario_id))
        if not aula:
            return False, 'Aula não encontrada.'

        if action == 'aprovar':
            aula.status = 'confirmado'
            message = f'Aula de {aula.disciplina.materia} aprovada.'
        elif action == 'negar':
            db.session.delete(aula)
            message = f'Solicitação de aula de {aula.disciplina.materia} foi negada e removida.'
        else:
            return False, 'Ação inválida.'
            
        db.session.commit()
        return True, message