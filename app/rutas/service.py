
# backend/app/rutas/service.py
from fastapi import APIRouter, Depends, Header
from jose import jwt, JWTError
from ..core import service_logic, user_logic
from ..models import ServiceBase
from ..config import settings
from ..utils import responses as res

router = APIRouter(prefix="/services", tags=["Services"])

def verify_admin_token(authorization: str = Header(...)):
    """
    Verifica que el token pertenezca a un administrador.
    
    Args:
        authorization (str): Token de autorización.
    
    Returns:
        dict: Datos del usuario administrador.
    
    Raises:
        HTTPException: Si el token es inválido o el usuario no es administrador.
    """
    if not authorization.startswith("Bearer "):
        return res.unauthorized("Invalid token header")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        user = user_logic.get_user_by_email(email)
        if not user:
            return res.not_found("User not found")
        if user["id_role"] != 1:
            return res.forbidden("Admin privileges required")
        return user
    except JWTError:
        return res.unauthorized("Invalid or expired token")


@router.get("/")
def list_services():
    """
    Lista todos los servicios.
    
    Returns:
        list[ServiceOut]: Lista de servicios.
    
    Raises:
        HTTPException: Si hay un error al obtener los servicios.
    """
    try:
        data = service_logic.get_all_services()
        # Convierte todos los campos Decimal a float por seguridad
        data_serializable = [service_logic.serialize_service(d) for d in data]
        return res.ok("Services listed successfully", data_serializable)
    except Exception as e:
        return res.server_error(f"Error listing services: {str(e)}")


@router.get("/{id_service}")
def get_service(id_service: int):
    """
    Obtiene un servicio por su ID.
    
    Args:
        id_service (int): ID del servicio.
    
    Returns:
        ServiceOut: Datos del servicio.
    
    Raises:
        HTTPException: Si el servicio no se encuentra o hay un error.
    """
    try:
        service = service_logic.get_service_by_id(id_service)
        if not service:
            return res.not_found("Service not found")
        return res.ok("Service retrieved successfully", service)
    except Exception as e:
        return res.server_error(f"Error getting service: {str(e)}")


@router.post("/", dependencies=[Depends(verify_admin_token)])
def create_service(data: ServiceBase):
    """
    Crea un nuevo servicio.
    
    Args:
        data (ServiceBase): Datos del servicio a crear.
    
    Returns:
        dict: Mensaje de confirmación y ID del nuevo servicio.
    
    Raises:
        HTTPException: Si hay un error al crear el servicio.
    """
    try:
        new_id = service_logic.create_service(data.dict())
        return res.accepted("Service created", {"id_service": new_id})
    except Exception as e:
        return res.server_error(f"Error creating service: {str(e)}")


@router.put("/{id_service}", dependencies=[Depends(verify_admin_token)])
def update_service(id_service: int, data: ServiceBase):
    """
    Actualiza un servicio existente.
    
    Args:
        id_service (int): ID del servicio a actualizar.
        data (ServiceBase): Nuevos datos del servicio.
    
    Returns:
        dict: Mensaje de confirmación.
    
    Raises:
        HTTPException: Si el servicio no se encuentra o hay un error al actualizarlo.
    """
    try:
        existing = service_logic.get_service_by_id(id_service)
        if not existing:
            return res.not_found("Service not found")
        service_logic.update_service(id_service, data.dict())
        return res.ok("Service updated successfully")
    except Exception as e:
        return res.server_error(f"Error updating service: {str(e)}")


@router.delete("/{id_service}", dependencies=[Depends(verify_admin_token)])
def delete_service(id_service: int):
    """
    Elimina un servicio.
    
    Args:
        id_service (int): ID del servicio a eliminar.
    
    Returns:
        dict: Mensaje de confirmación.
    
    Raises:
        HTTPException: Si el servicio no se encuentra o hay un error al eliminarlo.
    """
    try:
        existing = service_logic.get_service_by_id(id_service)
        if not existing:
            return res.not_found("Service not found")
        service_logic.delete_service(id_service)
        return res.ok("Service deleted successfully")
    except Exception as e:
        return res.server_error(f"Error deleting service: {str(e)}")
