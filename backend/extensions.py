import logging
import os
import warnings

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

# URL do Redis usado para rate limiting; pode ser sobrescrito via env var
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def _choose_storage():
    """Escolhe o storage para o Limiter.

    Tenta conectar ao Redis rapidamente; se falhar, em ambiente de produção lança
    RuntimeError (fail-fast). Em outros ambientes emite um warning e retorna
    o storage em memória.
    """
    try:
        # import local para evitar import-errors quando redis não estiver instalado
        import redis as _redis  # type: ignore

        client = _redis.from_url(REDIS_URL, socket_connect_timeout=1)
        client.ping()
        storage = REDIS_URL
    except Exception as exc:  # noqa: BLE001 - aceitável capturar broad para fallback
        is_production = os.environ.get("FLASK_ENV", "").lower() == "production"
        if is_production:
            raise RuntimeError(
                f"Falha ao conectar ao Redis em {REDIS_URL}: {exc}. Em produção o Redis deve estar acessível."
            )

        # emitir warning simples e usar storage em memória
        warnings.warn(
            f"Redis não disponível em {REDIS_URL}: {exc}. Usando storage em memória como fallback. "
            "Isto não é recomendado em produção.",
            stacklevel=2,
        )
        storage = "memory://"

    logger.info("Rate limiter storage: %s", storage)
    return storage


# Instância do Limiter usada pela aplicação. Ao importar este módulo o limiter
# é inicializado com o storage adequado.
limiter = Limiter(key_func=get_remote_address, storage_uri=_choose_storage())

__all__ = ["limiter"]
