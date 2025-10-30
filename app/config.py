# backend/app/config.py
"""
Módulo de Configuración
=======================
Carga y valida las variables de entorno para la configuración de la aplicación.
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache
import logging

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
#ENV_PATH = BASE_DIR.parent / ".env"  # PROYECTO_RESERVAS/.env
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    """
    Clase que define y valida las configuraciones de la aplicación.

    Attributes:
        APP_NAME (str): Nombre de la aplicación.
        APP_VERSION (str): Versión de la aplicación.
        DEBUG (bool): Modo de depuración.
        MYSQL_HOST (str): Host de MySQL.
        MYSQL_PORT (int): Puerto de MySQL.
        MYSQL_USER (str): Usuario de MySQL.
        MYSQL_PASSWORD (str): Contraseña de MySQL.
        MYSQL_DATABASE (str): Nombre de la base de datos MySQL.
        MYSQL_ROOT_PASSWORD (str): Contraseña de root de MySQL.
        SECRET_KEY (str): Clave secreta para tokens.
        ALGORITHM (str): Algoritmo de encriptación.
        ACCESS_TOKEN_EXPIRE_MINUTES (int): Tiempo de expiración del token de acceso.
    """
    # Configuración de la aplicación
    APP_NAME: str = "Centro de Belleza"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Configuración de MySQL
    MYSQL_HOST: str
    MYSQL_PORT: int = 3306
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str
    MYSQL_ROOT_PASSWORD: str

    # Configuración de seguridad
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ENV_PATH
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
        """
        Obtiene una instancia de Settings con caché.

        Returns:
            Settings: Instancia de la configuración.
        """
        try: 
            return Settings()
        except Exception as e:
            logging.error(f"Error al cargar la configuración: {str(e)}")
            raise

settings = get_settings()