# backend/app/rutas/upload_excel.py
import json
import time
import logging
from decimal import Decimal
from datetime import datetime, date
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Header
from jose import jwt, JWTError

from app.config import settings
from app.core import user_logic, logic_upload_excel
from app.utils.responses import build_response, unauthorized, forbidden, not_found, server_error

router = APIRouter(prefix="/upload", tags=["Excel Upload WS"])

# ======================================================
# Validar token de administrador para WebSocket
# ======================================================
async def verify_admin_token_ws(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        user = user_logic.get_user_by_email(email)

        if not user:
            return None, "Usuario no encontrado."
        if user.get("id_role") != 1:
            return None, "No autorizado para esta acción."

        return user, None
    except JWTError:
        return None, "Token inválido o expirado."
    except Exception as e:
        logging.exception("Error verificando token")
        return None, f"Error al verificar token: {str(e)}"


# para la serializacion

def serialize_any(value):
    if isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, (datetime, date)):
        # convierte datetime y date a string ISO
        return value.isoformat()
    elif isinstance(value, list):
        return [serialize_any(v) for v in value]
    elif isinstance(value, dict):
        return {k: serialize_any(v) for k, v in value.items()}
    return value


# ======================================================
# WebSocket para carga de Excel con progreso en tiempo real
# ======================================================
@router.websocket("/excel/")
async def upload_excel(websocket: WebSocket):
    """
    WebSocket que recibe uno o varios archivos Excel para procesarlos y generar una previsualización.
    Valida el token de administrador, decodifica los archivos en base64 y delega el procesamiento
    a `logic_upload_excel.handle_excel_upload_ws`.

    Parámetros:
        websocket (WebSocket): Conexión WebSocket abierta con el cliente.

    Mensajes entrantes:
        {
            "token": "JWT del usuario",
            "files": [
                { "filename": "archivo.xlsx", "content": "<base64>" },
                ...
            ]
        }

    Mensajes salientes:
        - Progreso de carga por archivo.
        - Resultado final con hojas válidas e inválidas.

    Retorna:
        WebSocket con mensajes JSON en tiempo real (no retorna HTTP Response).
    """
    await websocket.accept()
    try:
        init_data = await websocket.receive_text()
        payload = json.loads(init_data)
        token = payload.get("token")
        files = payload.get("files")

        user, error = await verify_admin_token_ws(token)
        if error:
            await websocket.send_text(json.dumps(build_response(False, error, None, 401).body.decode()))
            await websocket.close()
            return

        if not files:
            await websocket.send_text(json.dumps(build_response(False, "No se enviaron archivos.", None, 400).body.decode()))
            await websocket.close()
            return

        if len(files) > 5:
            await websocket.send_text(json.dumps(build_response(False, "Máximo 5 archivos permitidos.", None, 400).body.decode()))
            await websocket.close()
            return

        result = await logic_upload_excel.handle_excel_upload_ws(user["id_user"], files, websocket, time.time())

        # Enviar confirmación final antes de cerrar
        response_data = {
            "success": True,
            "message": "Previsualización cargada correctamente",
            "data": result
        }
        await websocket.send_text(json.dumps(response_data))
        await websocket.close()

    except WebSocketDisconnect:
        logging.warning("Cliente desconectado.")
    except Exception as e:
        logging.exception("Error en WebSocket de carga Excel")
        await websocket.send_text(json.dumps(build_response(False, f"Error: {str(e)}", None, 500).body.decode()))
        await websocket.close()


# ======================================================
# Obtener previsualización de las hojas cargadas
# ======================================================
@router.get("/sheets")
def get_uploaded_sheets(Authorization: str = Header(...)):
    """
    Obtiene la previsualización de los datos cargados por el usuario autenticado.
    Incluye tanto las hojas válidas como las que contienen errores.

    Parámetros:
        Authorization (str): Encabezado con el token Bearer del usuario.

    Retorna:
        JSON con estructura:
        {
            "success": true,
            "message": "Previsualización cargada correctamente",
            "data": {
                "sheets": {...},
                "summary": {...}
            }
        }
    """
    if not Authorization.startswith("Bearer "):
        return unauthorized("Formato de token inválido.")

    token = Authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        user = user_logic.get_user_by_email(email)
        if not user:
            return not_found("Usuario no encontrado.")
        if user.get("id_role") != 1:
            return forbidden("No autorizado para esta acción.")
    except JWTError:
        return unauthorized("Token inválido o expirado.")
    except Exception as e:
        logging.exception("Error verificando token")
        return server_error(str(e))

    data = logic_upload_excel.get_uploaded_sheets_by_user(user["id_user"])

    #Serializar cualquier Decimal en estructura anidada
    data = serialize_any(data)

    return build_response(True, "Previsualización cargada correctamente", data)


# ======================================================
# Actualizar un registro específico de la previsualización
# ======================================================
@router.put("/sheets/{id_import}")
def update_imported_row(id_import: int, updates: dict, Authorization: str = Header(...)):
    """
    Actualiza un registro específico en la tabla temporal data_imported.

    Parámetros:
        id_import (int): ID del registro a actualizar.
        updates (dict): Campos y valores a actualizar (name, description, duration_minutes, price, state).
        Authorization (str): Token Bearer del administrador.

    Body esperado:
    {
        "name": "Nuevo nombre",
        "description": "Nueva descripción",
        "duration_minutes": 30,
        "price": 25000.50,
        "state": true
    }

    Retorna:
        JSON con estructura estándar:
        {
            "success": true/false,
            "message": "Descripción del resultado",
            "data": { "id_import": int } | null
        }
    """
    if not Authorization.startswith("Bearer "):
        return unauthorized("Formato de token inválido.")

    token = Authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        user = user_logic.get_user_by_email(email)
        if not user:
            return not_found("Usuario no encontrado.")
        if user.get("id_role") != 1:
            return forbidden("No autorizado para esta acción.")
    except JWTError:
        return unauthorized("Token inválido o expirado.")
    except Exception as e:
        logging.exception("Error verificando token")
        return server_error(str(e))

    # Validar que el body no esté vacío
    if not updates or not isinstance(updates, dict):
        return build_response(False, "Datos de actualización inválidos", None, 400)

    # Intentar actualizar
    success, message = logic_upload_excel.update_imported_row(user["id_user"], id_import, updates)
    
    if success:
        return build_response(True, message, {"id_import": id_import})
    else:
        return build_response(False, message, None, 400)
    

# ======================================================
# Cancelar previsualización - Eliminar datos temporales
# ======================================================
@router.delete("/sheets/cancel")
def cancel_preview(Authorization: str = Header(...)):
    """
    Elimina todos los datos temporales (data_imported y data_errors) del usuario autenticado.
    Útil cuando el usuario decide cancelar la previsualización sin confirmar los datos.
    """
    if not Authorization.startswith("Bearer "):
        return unauthorized("Formato de token inválido.")

    token = Authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        user = user_logic.get_user_by_email(email)
        if not user:
            return not_found("Usuario no encontrado.")
        if user.get("id_role") != 1:
            return forbidden("No autorizado para esta acción.")
    except JWTError:
        return unauthorized("Token inválido o expirado.")
    except Exception as e:
        logging.exception("Error verificando token")
        return server_error(str(e))

    # Cancelar previsualización
    success, message, stats = logic_upload_excel.cancel_user_preview(user["id_user"])
    
    if success:
        return build_response(True, message, stats)
    else:
        return build_response(False, message, None, 500)
    
# ======================================================
# Confirmar y guardar datos en la tabla final (service)
# ======================================================
@router.websocket("/confirm/")
async def confirm_import_ws(websocket: WebSocket):
    """
    WebSocket para confirmar e insertar datos desde data_imported a service.
    Envía progreso en tiempo real por cada registro procesado.
    
    Mensaje inicial esperado:
    {
        "token": "...",
        "selected_sheets": ["Hoja1", "Hoja2"]
    }
    """
    await websocket.accept()
    try:
        init_data = await websocket.receive_text()
        payload = json.loads(init_data)
        token = payload.get("token")
        selected_sheets = payload.get("selected_sheets", [])

        # Validar token
        user, error = await verify_admin_token_ws(token)
        if error:
            await websocket.send_text(json.dumps({
                "success": False,
                "message": error,
                "code": 401
            }))
            await websocket.close()
            return

        # Validar que haya hojas seleccionadas
        if not selected_sheets or not isinstance(selected_sheets, list):
            await websocket.send_text(json.dumps({
                "success": False,
                "message": "Debes seleccionar al menos una hoja",
                "code": 400
            }))
            await websocket.close()
            return

        # Procesar confirmación
        result = await logic_upload_excel.confirm_import_to_service(
            user["id_user"],
            selected_sheets,
            websocket
        )

        # Enviar mensaje final
        await websocket.send_text(json.dumps({
            "success": True,
            "message": "Datos confirmados y guardados correctamente",
            "data": result
        }))
        await websocket.close()

    except WebSocketDisconnect:
        logging.warning("Cliente desconectado durante confirmación.")
    except Exception as e:
        logging.exception("Error en confirmación WebSocket")
        await websocket.send_text(json.dumps({
            "success": False,
            "message": f"Error: {str(e)}",
            "code": 500
        }))
        await websocket.close()