# backend/app/core/reservation_logic.py
import logging
from ..database import get_conn

def create_reservation(id_user: int, reservation_data: dict):
    """
    Crea una nueva reserva y bloquea el horario en el calendario.
    
    Args:
        id_user (int): ID del usuario que hace la reserva.
        reservation_data (dict): Datos de la reserva.
    
    Returns:
        int: ID de la nueva reserva.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)

            # 1️⃣ Validar servicio activo y obtener duración / precio
            cur.execute(
                "SELECT name, duration_minutes, price FROM service WHERE id_service = %s AND state = TRUE",
                (reservation_data["id_service"],)
            )
            service = cur.fetchone()
            if not service:
                raise ValueError("Service not found or inactive")

            total_price = service["price"]

            # 2️⃣ Crear reserva
            cur.execute(
                """INSERT INTO reservation 
                (id_user, id_service, id_reservation_status, start_datetime, end_datetime, total_price, payment_method, state)
                VALUES (%s, %s, 1, %s, %s, %s, %s, TRUE)""",
                (
                    id_user,
                    reservation_data["id_service"],
                    reservation_data["start_datetime"],
                    reservation_data["end_datetime"],
                    total_price,
                    reservation_data["payment_method"]
                )
            )
            new_id = cur.lastrowid

            # 3️⃣ Crear bloque en calendario
            cur.execute(
                """INSERT INTO calendar_block 
                (id_reservation, title, start_datetime, end_datetime, color, type, state)
                VALUES (%s, %s, %s, %s, '#b3ffb3', 'reservation', TRUE)""",
                (
                    new_id,
                    f"Reserva: {service['name']}",
                    reservation_data["start_datetime"],
                    reservation_data["end_datetime"]
                )
            )

            conn.commit()
            cur.close()
            return new_id

    except ValueError:
        raise
    except Exception as e:
        logging.error(f"Error al crear reserva: {str(e)}")
        raise

def get_user_reservations(id_user: int):
    """
    Obtiene todas las reservas de un usuario.
    
    Args:
        id_user (int): ID del usuario.
    
    Returns:
        list: Lista de reservas del usuario con información del servicio y estado.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT 
                    r.id_reservation,
                    r.id_user,
                    r.id_service,
                    r.id_reservation_status,
                    r.start_datetime,
                    r.end_datetime,
                    r.created_at,
                    r.total_price,
                    r.payment_method,
                    r.state,
                    s.name as service_name,
                    s.description as service_description,
                    s.duration_minutes,
                    rs.name as status_name
                FROM reservation r
                INNER JOIN service s ON r.id_service = s.id_service
                INNER JOIN reservation_status rs ON r.id_reservation_status = rs.id_reservation_status
                WHERE r.id_user = %s AND r.state = TRUE
                ORDER BY r.start_datetime DESC
            """, (id_user,))
            reservations = cur.fetchall()
            cur.close()
            
            # Convertir datetime objects a strings
            for reservation in reservations:
                for field in ['start_datetime', 'end_datetime', 'created_at']:
                    if reservation.get(field):
                        reservation[field] = reservation[field].strftime('%Y-%m-%d %H:%M:%S')
            
            return reservations if reservations else []
    except Exception as e:
        logging.error(f"Error al obtener reservas del usuario {id_user}: {str(e)}")
        raise

def get_all_reservations():
    """
    Obtiene todas las reservas con información completa de usuario, servicio y estado.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT 
                    r.id_reservation,
                    r.id_user,
                    r.id_service,
                    r.id_reservation_status,
                    r.start_datetime,
                    r.end_datetime,
                    r.created_at,
                    r.total_price,
                    r.payment_method,
                    r.state,
                    rs.name AS status_name,
                    s.name AS service_name,
                    s.description AS service_description,
                    COALESCE(up.first_name, '') AS first_name,
                    COALESCE(up.last_name, '') AS last_name,
                    COALESCE(ua.email, '') AS email
                FROM reservation r
                INNER JOIN reservation_status rs 
                    ON r.id_reservation_status = rs.id_reservation_status
                INNER JOIN service s 
                    ON r.id_service = s.id_service
                LEFT JOIN user_account ua 
                    ON r.id_user = ua.id_user
                LEFT JOIN user_profile up 
                    ON up.id_user = ua.id_user
                WHERE r.state = TRUE
                ORDER BY r.start_datetime DESC;
            """)
            reservations = cur.fetchall()
            cur.close()

            # Convertir datetime a string
            for reservation in reservations:
                for field in ['start_datetime', 'end_datetime', 'created_at']:
                    if reservation.get(field):
                        reservation[field] = reservation[field].strftime('%Y-%m-%d %H:%M:%S')

            return reservations or []
    except Exception as e:
        logging.error(f"Error al obtener todas las reservas: {str(e)}")
        raise

def get_reservation_by_id(id_reservation: int):
    """
    Obtiene una reserva por su ID.
    
    Args:
        id_reservation (int): ID de la reserva.
    
    Returns:
        dict: Datos de la reserva.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT 
                    r.id_reservation,
                    r.id_user,
                    r.id_service,
                    r.id_reservation_status,
                    r.start_datetime,
                    r.end_datetime,
                    r.created_at,
                    r.total_price,
                    r.payment_method,
                    r.state,
                    s.name as service_name,
                    rs.name as status_name
                FROM reservation r
                INNER JOIN service s ON r.id_service = s.id_service
                INNER JOIN reservation_status rs ON r.id_reservation_status = rs.id_reservation_status
                WHERE r.id_reservation = %s AND r.state = TRUE
            """, (id_reservation,))
            result = cur.fetchone()
            cur.close()
            
            # Convertir datetime objects a strings
            if result:
                if result['start_datetime']:
                    result['start_datetime'] = result['start_datetime'].strftime('%Y-%m-%d %H:%M:%S')
                if result['end_datetime']:
                    result['end_datetime'] = result['end_datetime'].strftime('%Y-%m-%d %H:%M:%S')
                if result['created_at']:
                    result['created_at'] = result['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            return result
    except Exception as e:
        logging.error(f"Error al obtener reserva con id {id_reservation}: {str(e)}")
        raise

def update_reservation_status(id_reservation: int, id_reservation_status: int):
    """
    Actualiza el estado de una reserva.
    
    Args:
        id_reservation (int): ID de la reserva.
        id_reservation_status (int): Nuevo ID del estado.
    
    Returns:
        bool: True si la actualización fue exitosa.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE reservation
                SET id_reservation_status = %s
                WHERE id_reservation = %s AND state = TRUE
            """, (id_reservation_status, id_reservation))
            conn.commit()
            cur.close()
            return True
    except Exception as e:
        logging.error(f"Error al actualizar estado de reserva {id_reservation}: {str(e)}")
        raise

def cancel_reservation(id_reservation: int, id_user: int):
    """
    Cancela una reserva (solo si pertenece al usuario).
    
    Args:
        id_reservation (int): ID de la reserva.
        id_user (int): ID del usuario que quiere cancelar.
    
    Returns:
        bool: True si la cancelación fue exitosa.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            
            # Verificar que la reserva pertenece al usuario
            cur.execute(
                "SELECT id_user FROM reservation WHERE id_reservation = %s AND state = TRUE",
                (id_reservation,)
            )
            reservation = cur.fetchone()
            
            if not reservation or reservation["id_user"] != id_user:
                raise ValueError("Reservation not found or unauthorized")
            
            # Cambiar estado a Cancelado (id_reservation_status = 3)
            cur.execute("""
                UPDATE reservation
                SET id_reservation_status = 3
                WHERE id_reservation = %s
            """, (id_reservation,))
            conn.commit()
            cur.close()
            return True
    except ValueError:
        raise
    except Exception as e:
        logging.error(f"Error al cancelar reserva {id_reservation}: {str(e)}")
        raise

def delete_reservation(id_reservation: int):
    """
    Elimina lógicamente una reserva.
    
    Args:
        id_reservation (int): ID de la reserva.
    
    Returns:
        bool: True si la eliminación fue exitosa.
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE reservation SET state = FALSE WHERE id_reservation = %s",
                (id_reservation,)
            )
            conn.commit()
            cur.close()
            return True
    except Exception as e:
        logging.error(f"Error al eliminar reserva {id_reservation}: {str(e)}")
        raise

