# Script para corrigir configurações de imagens do site
# Uso: python scripts/fix_site_images.py

from backend.models.database import db
from backend.services.site_config_service import SiteConfigService
from backend.app import create_app

app = create_app()

with app.app_context():
    # Corrige imagem de fundo geral
    SiteConfigService.set_config(
        key='site_background',
        value='/static/img/fundo.jpg',
        config_type='image',
        description='Imagem de fundo do site',
        category='general'
    )
    # Corrige imagem de fundo da navbar
    SiteConfigService.set_config(
        key='navbar_background_image',
        value='/static/img/fundo.jpg',
        config_type='image',
        description='Imagem de fundo da navbar',
        category='general'
    )
    db.session.commit()
    print('Configurações de imagens corrigidas!')
