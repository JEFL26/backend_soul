# backend/app/core/service_logic.py
"""
Lógica de Servicios
===================
Contiene las funciones CRUD para la gestión de servicios en la base de datos.
Incluye manejo de errores y registro de logs para rastrear fallos operativos.
"""

import logging
from ..database import get_conn
from decimal import Decimal

def serialize_service(row: dict):
    row_copy = row.copy()
    for k, v in row_copy.items():
        if isinstance(v, Decimal):
            row_copy[k] = float(v)
    return row_copy

def get_all_services():
    """
    Obtiene todos los servicios registrados en la base de datos.

    Returns:
        list[dict]: Lista de registros con la información de los servicios.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM service")
            rows = cur.fetchall()
            cur.close()
            return [serialize_service(r) for r in rows]
    except Exception as e:
        logging.error(f"Error al obtener todos los servicios: {str(e)}")
        raise


def get_service_by_id(id_service: int):
    """
    Obtiene un servicio específico por su ID.

    Args:
        id_service (int): Identificador del servicio.

    Returns:
        dict | None: Registro del servicio si existe, de lo contrario None.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM service WHERE id_service = %s", (id_service,))
            row = cur.fetchone()
            cur.close()
            if row is None:
                return None
            return serialize_service(row)
    except Exception as e:
        logging.error(f"Error al obtener servicio con id {id_service}: {str(e)}")
        raise

def create_service(data: dict):
    """
    Crea un nuevo servicio en la base de datos.

    Args:
        data (dict): Diccionario con los campos 'name', 'description',
                     'duration_minutes', 'price' y 'state'.

    Returns:
        int: ID del servicio recién creado.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO service (name, description, duration_minutes, price, state)
                   VALUES (%s, %s, %s, %s, %s)""",
                (data["name"], data.get("description"), data["duration_minutes"], data["price"], data["state"])
            )
            conn.commit()
            new_id = cur.lastrowid
            cur.close()
            return new_id
    except Exception as e:
        logging.error(f"Error al crear servicio: {str(e)}")
        raise


def update_service(id_service: int, data: dict):
    """
    Actualiza los datos de un servicio existente.

    Args:
        id_service (int): Identificador del servicio a actualizar.
        data (dict): Campos actualizados con sus nuevos valores.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """UPDATE service
                   SET name=%s, description=%s, duration_minutes=%s, price=%s, state=%s
                   WHERE id_service=%s""",
                (data["name"], data.get("description"), data["duration_minutes"], data["price"], data["state"], id_service)
            )
            conn.commit()
            cur.close()
    except Exception as e:
        logging.error(f"Error al actualizar servicio con id {id_service}: {str(e)}")
        raise


def delete_service(id_service: int):
    """
    Elimina un servicio por su ID.

    Args:
        id_service (int): Identificador del servicio a eliminar.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM service WHERE id_service = %s", (id_service,))
            conn.commit()
            cur.close()
    except Exception as e:
        logging.error(f"Error al eliminar servicio con id {id_service}: {str(e)}")
        raise