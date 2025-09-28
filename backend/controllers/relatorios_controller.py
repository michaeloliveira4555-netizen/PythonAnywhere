# backend/controllers/relatorios_controller.py

from flask import Blueprint, render_template, request, flash, Response, redirect, url_for
from flask_login import login_required
from datetime import datetime
import locale
import requests

from ..services.relatorio_service import RelatorioService
from ..services.instrutor_service import InstrutorService
from ..services.site_config_service import SiteConfigService
from utils.decorators import admin_or_programmer_required

# Configura o locale para Português do Brasil para traduzir o mês
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
    except locale.Error:
        print("Aviso: Locale 'pt_BR' não pôde ser configurado. Nomes de meses podem aparecer em inglês.")

relatorios_bp = Blueprint('relatorios', __name__, url_prefix='/relatorios')

# URL da API do WeasyPrint (container Docker)
WEASYPRINT_API_URL = "http://weasyprint:5001/pdf" # Usar o nome do serviço do docker-compose

def gerar_pdf_com_api(html_content):
    """Função para gerar PDF usando a API do WeasyPrint em um container Docker."""
    try:
        response = requests.post(
            WEASYPRINT_API_URL,
            json={'html': html_content},
            headers={'Content-Type': 'application/json'},
            timeout=30  # Timeout de 30 segundos
        )
        response.raise_for_status()  # Lança um erro para códigos de status HTTP 4xx/5xx
        return response.content
    except requests.exceptions.RequestException as e:
        # Captura erros de conexão, timeout, etc.
        raise Exception(f"Serviço de geração de PDF indisponível ou com erro: {e}")
    except Exception as e:
        raise Exception(f"Erro inesperado ao gerar PDF: {e}")


@relatorios_bp.route('/')
@login_required
@admin_or_programmer_required
def index():
    """Página que exibe os tipos de relatório disponíveis."""
    return render_template('relatorios/index.html')


@relatorios_bp.route('/gerar', methods=['GET', 'POST'])
@login_required
@admin_or_programmer_required
def gerar_relatorio_horas_aula():
    """
    Renderiza o formulário e processa a geração dos relatórios de horas-aula.
    """
    report_type = request.args.get('tipo', 'mensal')
    tipo_relatorio_titulo = report_type.replace("_", " ").title()
    
    # Busca todos os instrutores para popular o seletor no formulário
    todos_instrutores = InstrutorService.get_all_instrutores() if report_type == 'por_instrutor' else None

    if request.method == 'POST':
        # 1. Coleta e valida os dados do formulário
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')
        action = request.form.get('action') # 'preview' ou 'download'

        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash('Formato de data inválido. Use AAAA-MM-DD.', 'danger')
            return redirect(url_for('relatorios.gerar_relatorio_horas_aula', tipo=report_type))

        # 2. Prepara os filtros para o serviço com base no tipo de relatório
        is_rr_filter = report_type == 'efetivo_rr'
        instrutor_ids_filter = None
        if report_type == 'por_instrutor':
            instrutor_ids_filter = [int(id) for id in request.form.getlist('instrutor_ids')]
            if not instrutor_ids_filter:
                flash('Por favor, selecione pelo menos um instrutor.', 'warning')
                return redirect(url_for('relatorios.gerar_relatorio_horas_aula', tipo=report_type))

        # 3. Chama o serviço para obter os dados processados
        dados_relatorio = RelatorioService.get_horas_aula_por_instrutor(
            data_inicio, data_fim, is_rr_filter, instrutor_ids_filter
        )

        # 4. Prepara o contexto para renderizar o template do PDF
        contexto_pdf = {
            "dados": dados_relatorio,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "titulo_curso": request.form.get('curso_nome', 'Curso Técnico em Segurança Pública'),
            "nome_mes_ano": data_inicio.strftime("%B de %Y").capitalize(),
            "comandante_nome": request.form.get('comandante_nome', ''),
            "auxiliar_nome": request.form.get('auxiliar_nome', ''),
            "valor_hora_aula": 55.19 # Valor fixo ou buscar de config
        }

        # 5. Renderiza o HTML do relatório
        rendered_html = render_template('relatorios/pdf_template.html', **contexto_pdf)

        if action == 'preview':
            return rendered_html

        if action == 'download':
            try:
                # 6. Chama a API para converter o HTML em PDF
                pdf_content = gerar_pdf_com_api(rendered_html)
                
                return Response(
                    pdf_content,
                    mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment; filename=relatorio_horas_aula.pdf'}
                )
            except Exception as e:
                flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
                return redirect(url_for('relatorios.gerar_relatorio_horas_aula', tipo=report_type))

    # Se for GET, apenas exibe o formulário
    return render_template('relatorios/horas_aula_form.html', 
                           tipo_relatorio=tipo_relatorio_titulo, 
                           todos_instrutores=todos_instrutores)