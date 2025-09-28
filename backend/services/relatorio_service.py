# backend/services/relatorio_service.py

from ..models.database import db
from ..models.horario import Horario
from ..models.semana import Semana
from ..models.instrutor import Instrutor
from ..models.disciplina import Disciplina
from ..models.user import User
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload
from collections import defaultdict

class RelatorioService:
    @staticmethod
    def get_horas_aula_por_instrutor(data_inicio, data_fim, is_rr_filter=False, instrutor_ids_filter=None):
        """
        Busca e totaliza as horas-aula por instrutor e disciplina para um determinado período.
        
        Args:
            data_inicio (date): A data de início do período do relatório.
            data_fim (date): A data de fim do período do relatório.
            is_rr_filter (bool): Se True, filtra apenas instrutores da reserva (RR).
            instrutor_ids_filter (list): Uma lista de IDs de instrutores para filtrar.

        Returns:
            list: Uma lista de dicionários, cada um representando um instrutor e suas aulas.
        """
        # 1. Encontrar todas as semanas que se sobrepõem ao período solicitado.
        semanas_no_periodo_ids = db.session.scalars(
            select(Semana.id).where(
                Semana.data_inicio <= data_fim,
                Semana.data_fim >= data_inicio
            )
        ).all()

        if not semanas_no_periodo_ids:
            return []

        # 2. Construir a query base para buscar as aulas confirmadas no período.
        query = (
            select(
                Horario.instrutor_id,
                Horario.disciplina_id,
                func.sum(Horario.duracao).label('ch_a_pagar')
            )
            .join(Instrutor, Horario.instrutor_id == Instrutor.id)
            .where(
                Horario.semana_id.in_(semanas_no_periodo_ids),
                Horario.status == 'confirmado'
            )
        )

        # 3. Aplicar filtros opcionais
        if is_rr_filter:
            query = query.where(Instrutor.is_rr == True)
        
        if instrutor_ids_filter:
            query = query.where(Horario.instrutor_id.in_(instrutor_ids_filter))

        # 4. Agrupar os resultados por instrutor e disciplina
        aulas_agrupadas = db.session.execute(
            query.group_by(Horario.instrutor_id, Horario.disciplina_id)
        ).all()

        if not aulas_agrupadas:
            return []
            
        # 5. Estruturar os dados para o template do relatório
        instrutor_ids = {aula.instrutor_id for aula in aulas_agrupadas}
        
        # Pré-carrega todos os dados de instrutores e disciplinas necessários para evitar múltiplas queries
        instrutores_map = {
            i.id: i for i in db.session.scalars(
                select(Instrutor).options(joinedload(Instrutor.user)).where(Instrutor.id.in_(instrutor_ids))
            ).all()
        }
        disciplinas_map = {
            d.id: d for d in db.session.scalars(select(Disciplina)).all()
        }

        # Organiza os dados em uma estrutura aninhada
        dados_formatados = defaultdict(lambda: {'info': None, 'disciplinas': []})
        for aula in aulas_agrupadas:
            instrutor = instrutores_map.get(aula.instrutor_id)
            if instrutor:
                dados_formatados[aula.instrutor_id]['info'] = instrutor
                
                disciplina_info = {
                    'nome': disciplinas_map.get(aula.disciplina_id).materia if aula.disciplina_id in disciplinas_map else "N/D",
                    'ch_total': disciplinas_map.get(aula.disciplina_id).carga_horaria_prevista if aula.disciplina_id in disciplinas_map else 0,
                    'ch_paga_anteriormente': 0, # Lógica a ser implementada se necessário
                    'ch_a_pagar': aula.ch_a_pagar
                }
                dados_formatados[aula.instrutor_id]['disciplinas'].append(disciplina_info)
        
        # Converte o defaultdict para uma lista e ordena pelo nome do instrutor
        resultado_final = sorted(
            dados_formatados.values(),
            key=lambda item: item['info'].user.nome_completo or ''
        )

        return resultado_final