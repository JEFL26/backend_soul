# backend/app/rutas/reservation.py
from fastapi import APIRouter, Depends, Header
from ..core import reservation_logic, user_logic
from ..models import ReservationCreate, ReservationOut
from jose import jwt, JWTError
from ..config import settings
from app.utils.responses import (
    ok,
    bad_request,
    not_found,
    server_error,
    unauthorized,
    forbidden
)
import logging
from decimal import Decimal

router = APIRouter(prefix="/reservations", tags=["Reservations"])

def serialize_service(row: dict):
    row_copy = row.copy()
    for k, v in row_copy.items():
        if isinstance(v, Decimal):
            row_copy[k] = float(v)
    return row_copy

def get_current_user(authorization: str = Header(...)):
    """
    Obtiene el usuario actual desde el token JWT.
    
    Args:
        authorization (str): Token de autorización.
    
    Returns:
        dict: Datos del usuario autenticado.
    """
    if not authorization.startswith("Bearer "):
        return unauthorized("Invalid token header")

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        user = user_logic.get_user_by_email(email)
        if not user:
            return not_found("User not found")
        return user
    except JWTError:
        return unauthorized("Invalid or expired token")
    except Exception as e:
        logging.exception("Error decoding token")
        return server_error(f"Token error: {str(e)}")


def verify_admin_token(authorization: str = Header(...)):
    """
    Verifica que el token pertenezca a un administrador.
    
    Args:
        authorization (str): Token de autorización.
    
    Returns:
        dict: Datos del usuario administrador.
    """
    user = get_current_user(authorization)
    # Si la validación devolvió una respuesta uniforme (no un dict), retornarla directamente
    if not isinstance(user, dict):
        return user
    if user["id_role"] != 1:  # solo admin (id_role=1)
        return forbidden("Admin privileges required")
    return user


@router.post("/")
def create_reservation(data: ReservationCreate, user: dict = Depends(get_current_user)):
    """
    Crea una nueva reserva con inicio y fin específicos.
    
    Args:
        data (ReservationCreate): Datos de la reserva.
        user (dict): Usuario autenticado.
    
    Returns:
        JSONResponse: Mensaje de confirmación y ID de la nueva reserva.
    """
    try:
        # Si user no es dict (error de autenticación)
        if not isinstance(user, dict):
            return user

        new_id = reservation_logic.create_reservation(user["id_user"], data.dict())
        return ok("Reservation created successfully", {"id_reservation": new_id})
    except ValueError as e:
        return bad_request(str(e))
    except Exception as e:
        logging.exception("Error creating reservation")
        return server_error(f"Error creating reservation: {str(e)}")


@router.get("/my-reservations")
def get_my_reservations(user: dict = Depends(get_current_user)):
    """
    Obtiene todas las reservas del usuario autenticado.
    
    Args:
        user (dict): Usuario autenticado.
    
    Returns:
        JSONResponse: Lista de reservas del usuario.
    """
    try:
        if not isinstance(user, dict):
            return user

        reservations = reservation_logic.get_user_reservations(user["id_user"])
        # Convertir Decimal a float
        reservations = [serialize_service(r) for r in reservations]
        return ok("User reservations retrieved", reservations)
    except Exception as e:
        logging.exception("Error getting reservations")
        return server_error(f"Error getting reservations: {str(e)}")


@router.get("/")
def get_all_reservations(user: dict = Depends(verify_admin_token)):
    """
    Obtiene todas las reservas del sistema (solo para administradores).
    
    Args:
        user (dict): Usuario administrador.
    
    Returns:
        JSONResponse: Lista de todas las reservas.
    """
    try:
        if not isinstance(user, dict):
            return user

        reservations = reservation_logic.get_all_reservations()
        reservations = [serialize_service(r) for r in reservations]
        return ok("All reservations retrieved", reservations)
    except Exception as e:
        logging.exception("Error getting all reservations")
        return server_error(f"Error getting reservations: {str(e)}")


@router.get("/{id_reservation}")
def get_reservation(id_reservation: int, user: dict = Depends(get_current_user)):
    """
    Obtiene una reserva por su ID.
    
    Args:
        id_reservation (int): ID de la reserva.
        user (dict): Usuario autenticado.
    
    Returns:
        JSONResponse: Datos de la reserva.
    """
    try:
        if not isinstance(user, dict):
            return user

        reservation = reservation_logic.get_reservation_by_id(id_reservation)
        if not reservation:
            return not_found("Reservation not found")
        
        if reservation:
            reservation = serialize_service(reservation)

        # Verificar que la reserva pertenece al usuario (a menos que sea admin)
        if user["id_role"] != 1 and reservation["id_user"] != user["id_user"]:
            return forbidden("You are not authorized to view this reservation")

        return ok("Reservation retrieved", reservation)
    except Exception as e:
        logging.exception("Error getting reservation")
        return server_error(f"Error getting reservation: {str(e)}")


@router.patch("/{id_reservation}/cancel")
def cancel_reservation(id_reservation: int, user: dict = Depends(get_current_user)):
    """
    Cancela una reserva del usuario autenticado.
    
    Args:
        id_reservation (int): ID de la reserva.
        user (dict): Usuario autenticado.
    
    Returns:
        JSONResponse: Mensaje de confirmación.
    """
    try:
        if not isinstance(user, dict):
            return user

        reservation_logic.cancel_reservation(id_reservation, user["id_user"])
        return ok("Reservation cancelled successfully")
    except ValueError as e:
        return bad_request(str(e))
    except Exception as e:
        logging.exception("Error cancelling reservation")
        return server_error(f"Error cancelling reservation: {str(e)}")


@router.patch("/{id_reservation}/status/{id_status}")
def update_reservation_status(
    id_reservation: int,
    id_status: int,
    user: dict = Depends(verify_admin_token)
):
    """
    Actualiza el estado de una reserva (solo para administradores).
    
    Args:
        id_reservation (int): ID de la reserva.
        id_status (int): Nuevo ID del estado.
        user (dict): Usuario administrador.
    
    Returns:
        JSONResponse: Mensaje de confirmación.
    """
    try:
        if not isinstance(user, dict):
            return user

        reservation_logic.update_reservation_status(id_reservation, id_status)
        return ok("Reservation status updated successfully")
    except Exception as e:
        logging.exception("Error updating reservation status")
        return server_error(f"Error updating reservation status: {str(e)}")


@router.delete("/{id_reservation}")
def delete_reservation(id_reservation: int, user: dict = Depends(verify_admin_token)):
    """
    Elimina lógicamente una reserva (solo para administradores).
    
    Args:
        id_reservation (int): ID de la reserva.
        user (dict): Usuario administrador.
    
    Returns:
        JSONResponse: Mensaje de confirmación.
    """
    try:
        if not isinstance(user, dict):
            return user

        reservation_logic.delete_reservation(id_reservation)
        return ok("Reservation deleted successfully")
    except Exception as e:
        logging.exception("Error deleting reservation")
        return server_error(f"Error deleting reservation: {str(e)}")
