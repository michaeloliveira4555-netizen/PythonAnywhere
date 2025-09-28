from sqlalchemy import select
from backend.models.database import db
from backend.models.site_config import SiteConfig
from flask import current_app
import re

class SiteConfigService:

    _DEFAULT_CONFIGS = [
        # Configurações gerais
        ('site_background', '', 'image', 'Imagem de fundo do site', 'general'),
        ('site_logo', '', 'image', 'Logo principal do site', 'general'),
        ('primary_color', '#3b82f6', 'color', 'Cor primária do site', 'general'),
        ('secondary_color', '#1a232c', 'color', 'Cor secundária do site', 'general'),
        ('navbar_background_image', '', 'image', 'Imagem de fundo da barra de navegação', 'general'),
        
        # Ícones do dashboard
        ('dashboard_card_alunos_icon', '👥', 'text', 'Ícone do card Alunos', 'dashboard'),
        ('dashboard_card_instrutores_icon', '🎓', 'text', 'Ícone do card Instrutores', 'dashboard'),
        ('dashboard_card_disciplinas_icon', '📚', 'text', 'Ícone do card Disciplinas', 'dashboard'),
        ('dashboard_card_historico_icon', '📊', 'text', 'Ícone do card Histórico', 'dashboard'),
        ('dashboard_card_assets_icon', '🎨', 'text', 'Ícone do card Assets', 'dashboard'),
        
        # Imagens de fundo dos cards
        ('dashboard_card_alunos_bg', '', 'image', 'Imagem de fundo do card Alunos', 'dashboard'),
        ('dashboard_card_instrutores_bg', '', 'image', 'Imagem de fundo do card Instrutores', 'dashboard'),
        ('dashboard_card_disciplinas_bg', '', 'image', 'Imagem de fundo do card Disciplinas', 'dashboard'),
        ('dashboard_card_historico_bg', '', 'image', 'Imagem de fundo do card Histórico', 'dashboard'),
        ('dashboard_card_assets_bg', '', 'image', 'Imagem de fundo do card Assets', 'dashboard'),
        ('dashboard_card_customizer_bg', '', 'image', 'Imagem de fundo do card Customizar', 'dashboard'),
        ('dashboard_header_bg', '', 'image', 'Imagem de fundo do cabeçalho do dashboard', 'dashboard'),
        
        # Sidebar
        ('sidebar_logo', '', 'image', 'Logo da sidebar', 'sidebar'),

        # Ícones das Turmas (NOVA SEÇÃO)
        ('turma_1_icon', '', 'image', 'Ícone da Turma 1', 'turmas'),
        ('turma_2_icon', '', 'image', 'Ícone da Turma 2', 'turmas'),
        ('turma_3_icon', '', 'image', 'Ícone da Turma 3', 'turmas'),
        ('turma_4_icon', '', 'image', 'Ícone da Turma 4', 'turmas'),
        ('turma_5_icon', '', 'image', 'Ícone da Turma 5', 'turmas'),
        ('turma_6_icon', '', 'image', 'Ícone da Turma 6', 'turmas'),
        ('turma_7_icon', '', 'image', 'Ícone da Turma 7', 'turmas'),
        ('turma_8_icon', '', 'image', 'Ícone da Turma 8', 'turmas'),

        # Configurações de Relatórios
        ('report_chefe_ensino_cargo', 'Chefe da Seção de Ensino', 'text', 'Cargo padrão do Chefe de Ensino em relatórios', 'reports'),
        ('report_comandante_cargo', 'Comandante da EsFAS-SM', 'text', 'Cargo padrão do Comandante em relatórios', 'reports'),
        ('report_cidade_estado', 'Santa Maria - RS', 'text', 'Cidade e Estado padrão para relatórios', 'reports'),
    ]

    _CONFIG_KEYS = {d[0]: {'type': d[2], 'category': d[4]} for d in _DEFAULT_CONFIGS}

    @staticmethod
    def get_config(key: str, default_value: str = None):
        """Pega uma configuração do site"""
        config = db.session.execute(
            select(SiteConfig).where(SiteConfig.config_key == key)
        ).scalar_one_or_none()
        
        return config.config_value if config else default_value
    
    @staticmethod
    def set_config(key: str, value: str, config_type: str = 'text', 
                   description: str = None, category: str = 'general', 
                   updated_by: int = None):
        """Define uma configuração do site com validação"""
        # 1. Validar a chave da configuração (whitelist)
        if key not in SiteConfigService._CONFIG_KEYS:
            raise ValueError(f"Chave de configuração inválida: {key}")
        
        expected_type = SiteConfigService._CONFIG_KEYS[key]['type']
        if config_type != expected_type:
            raise ValueError(f"Tipo de configuração inválido para a chave {key}. Esperado: {expected_type}, Recebido: {config_type}")

        # 2. Validar o valor com base no tipo
        if expected_type == 'image':
            # Para imagens, o valor deve ser uma URL relativa para static/uploads
            # ou vazia. Não permitir URLs arbitrárias para prevenir XSS.
            if value and not (value.startswith('/static/uploads/') or value.startswith('http') or value.startswith('https')):
                raise ValueError(f"Valor inválido para configuração de imagem: {value}. Deve ser uma URL de asset válida.")
            # Further validation could check if the asset actually exists in ImageAsset table
        elif expected_type == 'color':
            # Validar formato de cor hexadecimal (ex: #RRGGBB ou #RGB)
            import re
            if value and not re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', value):
                raise ValueError(f"Valor inválido para configuração de cor: {value}. Esperado formato hexadecimal (#RRGGBB).")
        elif expected_type == 'text':
            # Para texto, podemos adicionar alguma sanitização básica se necessário,
            # mas o Jinja2 já faz auto-escaping por padrão, mitigando XSS.
            pass # Por enquanto, sem sanitização explícita para texto simples

        config = db.session.execute(
            select(SiteConfig).where(SiteConfig.config_key == key)
        ).scalar_one_or_none()
        
        if config:
            config.config_value = value
            config.config_type = config_type
            config.description = description # Pode ser atualizado
            config.category = category # Pode ser atualizado
            config.updated_by = updated_by
        else:
            config = SiteConfig(
                config_key=key,
                config_value=value,
                config_type=config_type,
                description=description,
                category=category,
                updated_by=updated_by
            )
            db.session.add(config)
        
        return config
    
    @staticmethod
    def get_all_configs():
        """Pega todas as configurações"""
        return db.session.execute(select(SiteConfig)).scalars().all()
    
    @staticmethod
    def get_configs_by_category(category: str):
        """Pega configurações por categoria"""
        return db.session.execute(
            select(SiteConfig).where(SiteConfig.category == category)
        ).scalars().all()
    
    @staticmethod
    def init_default_configs():
        """Inicializa configurações padrão"""
        for key, value, config_type, description, category in SiteConfigService._DEFAULT_CONFIGS:
            existing = db.session.execute(
                select(SiteConfig).where(SiteConfig.config_key == key)
            ).scalar_one_or_none()
            
            if not existing:
                config = SiteConfig(
                    config_key=key,
                    config_value=value,
                    config_type=config_type,
                    description=description,
                    category=category
                )
                db.session.add(config)
        
    @staticmethod
    def delete_all_configs():
        db.session.query(SiteConfig).delete()