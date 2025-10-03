# Script para definir corretamente as imagens de fundo e navbar
from backend.app import create_app
from backend.services.site_config_service import SiteConfigService
from backend.models.database import db

app = create_app()

with app.app_context():
    SiteConfigService.set_config(
        key='site_background',
        value='/static/img/fundo.jpg',
        config_type='image',
        description='Imagem de fundo do site',
        category='general'
    )
    SiteConfigService.set_config(
        key='navbar_background_image',
        value='/static/img/fundo.jpg',
        config_type='image',
        description='Imagem de fundo da navbar',
        category='general'
    )
    db.session.commit()
    print('Imagens de fundo e navbar definidas corretamente!')
