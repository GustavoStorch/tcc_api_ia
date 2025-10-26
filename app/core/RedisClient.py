import redis
import json
from .config import settings

def get_redis_client():
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True 
        )
        redis_client.ping()
        print(f"Conectado ao Redis com sucesso em {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        return redis_client
    except redis.exceptions.ConnectionError as e:
        print(f"Erro fatal: Não foi possível conectar ao Redis em {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        print(f"Erro: {e}")
        return None 
    except Exception as e:
        print(f"Erro inesperado ao inicializar o Redis: {e}")
        return None

redis_client = get_redis_client()