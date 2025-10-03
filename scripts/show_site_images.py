# Script para exibir valores atuais das configs de imagem
from backend.app import create_app
from backend.services.site_config_service import SiteConfigService

app = create_app()

with app.app_context():
    bg = SiteConfigService.get_config('site_background')
    navbar = SiteConfigService.get_config('navbar_background_image')
    print('site_background:', repr(bg))
    print('navbar_background_image:', repr(navbar))
