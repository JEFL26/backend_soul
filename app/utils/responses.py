# backend/app/utils/responses.py

from typing import Any, Optional, Dict
from fastapi import status
from fastapi.responses import JSONResponse

def build_response(
    success: bool = True,
    message: str = "",
    data: Optional[Any] = None,
    code: int = status.HTTP_200_OK,
    total: Optional[int] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None
) -> JSONResponse:
    """
    Construye una respuesta HTTP uniforme para todos los endpoints de la API.
    
    Parámetros:
      - success (bool): Indica si la operación fue exitosa (True/False).
      - message (str): Mensaje descriptivo de la operación.
      - data (Any, opcional): Datos que se desean devolver al cliente.
      - code (int): Código HTTP de la respuesta (por defecto 200 OK).
      - total (int, opcional): Total de registros (para paginación).
      - page (int, opcional): Página actual (para paginación).
      - page_size (int, opcional): Tamaño de página (para paginación).
    
    Retorna:
      - JSONResponse: Objeto JSON listo para devolver al cliente, con estructura:
          {
            "success": bool,
            "message": str,
            "data": any,
            "code": int,
            "total": int (opcional),
            "page": int (opcional),
            "page_size": int (opcional)
          }
        y con el status_code HTTP correspondiente.
    """
    payload: Dict[str, Any] = {
        "success": bool(success),
        "message": str(message) if message is not None else "",
        "data": data,
        "code": int(code)
    }
    
    # Agregar parámetros de paginación si se proporcionan
    if total is not None:
        payload["total"] = total
    if page is not None:
        payload["page"] = page
    if page_size is not None:
        payload["page_size"] = page_size

    return JSONResponse(content=payload, status_code=int(code))


# =========================
# Helpers rápidos para usar en endpoints
# =========================

def ok(message: str = "OK", data: Any = None):
    """
    Respuesta estándar para éxito HTTP 200.
    """
    return build_response(True, message, data, status.HTTP_200_OK)


def accepted(message: str = "Accepted", data: Any = None):
    """
    Respuesta estándar para éxito HTTP 202 (petición aceptada pero no procesada aún).
    """
    return build_response(True, message, data, status.HTTP_202_ACCEPTED)


def bad_request(message: str = "Bad request", data: Any = None):
    """
    Respuesta estándar para error HTTP 400 (solicitud incorrecta).
    """
    return build_response(False, message, data, status.HTTP_400_BAD_REQUEST)


def not_found(message: str = "Not found", data: Any = None):
    """
    Respuesta estándar para error HTTP 404 (recurso no encontrado).
    """
    return build_response(False, message, data, status.HTTP_404_NOT_FOUND)


def server_error(message: str = "Internal server error", data: Any = None):
    """
    Respuesta estándar para error HTTP 500 (error interno del servidor).
    """
    return build_response(False, message, data, status.HTTP_500_INTERNAL_SERVER_ERROR)

def unauthorized(message: str = "Unauthorized", data: Any = None):
    return build_response(False, message, data, status.HTTP_401_UNAUTHORIZED)

def forbidden(message: str = "Forbidden", data: Any = None):
    return build_response(False, message, data, status.HTTP_403_FORBIDDEN)
