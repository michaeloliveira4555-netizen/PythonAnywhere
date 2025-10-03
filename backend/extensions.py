
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# Configuração do Redis para rate limiting
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

limiter = Limiter(
	key_func=get_remote_address,
	storage_uri=REDIS_URL
)
