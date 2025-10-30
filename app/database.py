# backend/app/database.py
import logging
from mysql.connector import pooling, Error as MySQLError
from contextlib import contextmanager
from .config import settings

_pool = None

def init_pool():
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="fastapi_pool",
                pool_size=5,
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE,
                autocommit=True
            )
        except MySQLError as e:
            logging.exception("Error al inicializar el pool de conexiones")
            raise
        except Exception as e:
            logging.exception("Error inesperado inicializando el pool")
            raise
    return _pool

@contextmanager
def get_conn():
    """
    Context manager seguro para obtener una conexión del pool.
    Garantiza cierre y registra errores específicos de MySQL y otros.
    Uso:
        with get_conn() as conn:
            cur = conn.cursor()
            ...
    """
    pool = init_pool()
    conn = None
    try:
        conn = pool.get_connection()
        yield conn
    except MySQLError as e:
        logging.exception(f"MySQL error al obtener/usar la conexión: {e}")
        raise
    except Exception as e:
        logging.exception(f"Error inesperado al obtener/usar la conexión: {e}")
        raise
    finally:
        if conn is not None:
            try:
                # Intentar cerrar siempre la conexión devuelta al pool
                conn.close()
                logging.debug("Conexión DB cerrada/retornada al pool correctamente")
            except Exception as e:
                logging.exception(f"Error cerrando la conexión DB: {e}")

# Inicializar el pool al importar el módulo (si falla, lo logea)
try:
    init_pool()
except Exception as e:
    logging.exception(f"Error al inicializar el pool: {e}")