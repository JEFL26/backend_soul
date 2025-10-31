# backend_soul/app/rutas/usuarios.py
"""
Rutas para la gestión de usuarios (CRUD).

Endpoints:
- GET /api/v1/usuarios/ - Listar usuarios con paginación y filtros
- GET /api/v1/usuarios/{id_user} - Obtener un usuario por ID
- PUT /api/v1/usuarios/{id_user} - Actualizar un usuario
- DELETE /api/v1/usuarios/{id_user} - Desactivar un usuario (soft delete)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging
from ..database import get_conn
from ..models import UsuarioUpdate, UsuarioListOut
from ..utils.responses import build_response
from mysql.connector import Error as MySQLError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/usuarios",
    tags=["Usuarios"],
    responses={
        404: {"description": "Usuario no encontrado"},
        500: {"description": "Error del servidor"}
    }
)


def _map_usuario(user_data: dict) -> dict:
    """
    Mapea los datos de usuario de BD a formato frontend.
    Convierte campos de backend_soul a formato Centro de Belleza.
    """
    return {
        "id": user_data["id_user"],
        "nombre_completo": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
        "email": user_data["email"],
        "telefono": user_data.get("phone", ""),
        "rol": _get_role_name(user_data["id_role"]),
        "estado": user_data["state"],
        "fecha_registro": None  # backend_soul no guarda fecha de registro en user_account
    }


def _get_role_name(id_role: int) -> str:
    """Convierte ID de rol a nombre legible. Será dinámico en futuras versiones."""
    role_map = {
        1: "Estilista",  # empleado
        2: "Cliente",
        3: "Admin"
    }
    return role_map.get(id_role, "Cliente")


def _get_role_id(role_name: str) -> int:
    """Convierte nombre de rol a ID."""
    role_map = {
        "Estilista": 1,
        "Cliente": 2,
        "Admin": 3
    }
    return role_map.get(role_name, 2)  # Por defecto Cliente


def _parse_nombre_completo(nombre_completo: str) -> tuple:
    """Separa nombre completo en nombre y apellido."""
    partes = nombre_completo.strip().split(None, 1) if nombre_completo else ["", ""]
    first_name = partes[0] if len(partes) > 0 else ""
    last_name = partes[1] if len(partes) > 1 else ""
    return first_name, last_name


@router.get("/", response_model=dict)
async def listar_usuarios(
    skip: int = Query(0, ge=0, description="Saltar N usuarios"),
    limit: int = Query(10, ge=1, le=100, description="Límite de usuarios por página"),
    id_role: Optional[int] = Query(None, description="Filtrar por ID de rol"),
    rol: Optional[str] = Query(None, description="Filtrar por nombre de rol (Cliente, Estilista, Admin)"),
    estado: Optional[bool] = Query(None, description="Filtrar por estado (true/false)"),
    buscar: Optional[str] = Query(None, description="Buscar por nombre o email")
):
    """
    Obtiene lista de usuarios con paginación, filtros y búsqueda.
    
    **Parámetros de filtro:**
    - skip: Cantidad de registros a saltar (para paginación)
    - limit: Cantidad de registros por página
    - id_role: Filtrar por ID de rol
    - estado: Filtrar por estado (true=activo, false=inactivo)
    - buscar: Búsqueda por nombre o email
    
    **Respuesta:**
    - success (bool): Indica si la operación fue exitosa
    - data: Array de usuarios encontrados (mapeados a formato frontend)
    - total: Total de registros sin paginación
    - page: Página actual
    - page_size: Tamaño de página
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            
            # Construir query base
            where_clauses = []
            params = []
            
            # Manejar filtro de rol (aceptar tanto nombre como ID)
            if rol is not None:
                id_role = _get_role_id(rol)
            
            if id_role is not None:
                where_clauses.append("ua.id_role = %s")
                params.append(id_role)
            
            if estado is not None:
                where_clauses.append("ua.state = %s")
                params.append(estado)
            
            if buscar:
                where_clauses.append("(CONCAT(up.first_name, ' ', up.last_name) LIKE %s OR ua.email LIKE %s)")
                params.extend([f"%{buscar}%", f"%{buscar}%"])
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # Contar total
            count_query = f"""
                SELECT COUNT(*) as total
                FROM user_account ua
                LEFT JOIN user_profile up ON ua.id_user = up.id_user
                WHERE {where_clause}
            """
            cur.execute(count_query, params)
            total = cur.fetchone()["total"]
            
            # Obtener usuarios con paginación
            query = f"""
                SELECT 
                    ua.id_user,
                    ua.email,
                    ua.id_role,
                    ua.state,
                    up.first_name,
                    up.last_name,
                    up.phone
                FROM user_account ua
                LEFT JOIN user_profile up ON ua.id_user = up.id_user
                WHERE {where_clause}
                ORDER BY ua.id_user DESC
                LIMIT %s OFFSET %s
            """
            
            limit_offset_params = params + [limit, skip]
            cur.execute(query, limit_offset_params)
            usuarios = cur.fetchall()
            
            # Mapear usuarios al formato esperado por frontend
            usuarios_mapped = [_map_usuario(u) for u in usuarios]
            
            cur.close()
            
            logger.info(f"Listados {len(usuarios_mapped)} usuarios (total: {total})")
            
            page = (skip // limit) + 1 if limit > 0 else 1
            
            return build_response(
                success=True,
                data=usuarios_mapped,
                message="Usuarios obtenidos exitosamente",
                code=200,
                total=total,
                page=page,
                page_size=limit
            )
            
    except MySQLError as e:
        logger.error(f"Error MySQL al listar usuarios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    except Exception as e:
        logger.error(f"Error al listar usuarios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.post("/", response_model=dict)
async def crear_usuario(usuario_create: UsuarioUpdate):
    """
    Crea un nuevo usuario.
    
    **Parámetros:**
    - usuario_create: Datos del nuevo usuario
    
    **Respuesta:**
    - success (bool): Indica si la operación fue exitosa
    - data: Usuario creado (mapeado a formato frontend)
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            
            # Verificar que el email no existe
            cur.execute("SELECT id_user FROM user_account WHERE email = %s", (usuario_create.email,))
            if cur.fetchone():
                logger.warning(f"Intento de crear usuario con email existente: {usuario_create.email}")
                raise HTTPException(status_code=400, detail="El email ya está registrado")
            
            # Obtener ID del rol
            id_role = _get_role_id(usuario_create.rol) if usuario_create.rol else 2  # Por defecto Cliente
            
            # Crear usuario en user_account
            account_query = "INSERT INTO user_account (email, id_role, state) VALUES (%s, %s, %s)"
            cur.execute(account_query, (usuario_create.email, id_role, usuario_create.estado if usuario_create.estado is not None else True))
            conn.commit()
            
            # Obtener el ID del nuevo usuario
            cur.execute("SELECT LAST_INSERT_ID() as id_user")
            new_id_user = cur.fetchone()["id_user"]
            
            # Crear perfil del usuario si hay datos
            if usuario_create.nombre_completo or usuario_create.telefono:
                first_name, last_name = _parse_nombre_completo(usuario_create.nombre_completo or "")
                profile_query = "INSERT INTO user_profile (id_user, first_name, last_name, phone) VALUES (%s, %s, %s, %s)"
                cur.execute(profile_query, (new_id_user, first_name, last_name, usuario_create.telefono or ""))
                conn.commit()
            
            # Obtener el usuario creado
            query = """
                SELECT 
                    ua.id_user,
                    ua.email,
                    ua.id_role,
                    ua.state,
                    up.first_name,
                    up.last_name,
                    up.phone
                FROM user_account ua
                LEFT JOIN user_profile up ON ua.id_user = up.id_user
                WHERE ua.id_user = %s
            """
            
            cur.execute(query, (new_id_user,))
            usuario_creado = cur.fetchone()
            usuario_mapped = _map_usuario(usuario_creado)
            cur.close()
            
            logger.info(f"Usuario creado: ID {new_id_user}")
            return build_response(
                success=True,
                data=usuario_mapped,
                message="Usuario creado exitosamente",
                code=201
            )
            
    except MySQLError as e:
        logger.error(f"Error MySQL al crear usuario: {str(e)}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear usuario: {str(e)}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/{id_user}", response_model=dict)
async def obtener_usuario(id_user: int):
    """
    Obtiene un usuario por su ID.
    
    **Parámetros:**
    - id_user: ID del usuario a obtener
    
    **Respuesta:**
    - success (bool): Indica si la operación fue exitosa
    - data: Información del usuario (mapeado a formato frontend)
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    ua.id_user,
                    ua.email,
                    ua.id_role,
                    ua.state,
                    up.first_name,
                    up.last_name,
                    up.phone
                FROM user_account ua
                LEFT JOIN user_profile up ON ua.id_user = up.id_user
                WHERE ua.id_user = %s
            """
            
            cur.execute(query, (id_user,))
            usuario = cur.fetchone()
            cur.close()
            
            if not usuario:
                logger.warning(f"Usuario no encontrado: ID {id_user}")
                raise HTTPException(status_code=404, detail=f"Usuario con ID {id_user} no encontrado")
            
            usuario_mapped = _map_usuario(usuario)
            logger.info(f"Usuario obtenido: ID {id_user}")
            return build_response(
                success=True,
                data=usuario_mapped,
                message="Usuario obtenido exitosamente",
                code=200
            )
            
    except MySQLError as e:
        logger.error(f"Error MySQL al obtener usuario {id_user}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener usuario {id_user}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.put("/{id_user}", response_model=dict)
async def actualizar_usuario(id_user: int, usuario_update: UsuarioUpdate):
    """
    Actualiza los datos de un usuario.
    
    **Parámetros:**
    - id_user: ID del usuario a actualizar
    - usuario_update: Datos a actualizar (mapeados desde frontend)
    
    **Respuesta:**
    - success (bool): Indica si la operación fue exitosa
    - data: Usuario actualizado (mapeado a formato frontend)
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            
            # Verificar que el usuario existe
            cur.execute("SELECT id_user FROM user_account WHERE id_user = %s", (id_user,))
            if not cur.fetchone():
                logger.warning(f"Intento de actualizar usuario no existente: ID {id_user}")
                raise HTTPException(status_code=404, detail=f"Usuario con ID {id_user} no encontrado")
            
            # Actualizar user_profile si hay datos de perfil
            if usuario_update.nombre_completo or usuario_update.telefono:
                profile_updates = []
                profile_params = []
                
                if usuario_update.nombre_completo:
                    first_name, last_name = _parse_nombre_completo(usuario_update.nombre_completo)
                    profile_updates.append("first_name = %s")
                    profile_params.append(first_name)
                    profile_updates.append("last_name = %s")
                    profile_params.append(last_name)
                
                if usuario_update.telefono:
                    profile_updates.append("phone = %s")
                    profile_params.append(usuario_update.telefono)
                
                if profile_updates:
                    profile_query = f"UPDATE user_profile SET {', '.join(profile_updates)} WHERE id_user = %s"
                    profile_params.append(id_user)
                    cur.execute(profile_query, profile_params)
            
            # Actualizar user_account si hay datos de cuenta
            if usuario_update.rol is not None or usuario_update.estado is not None:
                account_updates = []
                account_params = []
                
                if usuario_update.rol is not None:
                    id_role = _get_role_id(usuario_update.rol)
                    account_updates.append("id_role = %s")
                    account_params.append(id_role)
                
                if usuario_update.estado is not None:
                    account_updates.append("state = %s")
                    account_params.append(usuario_update.estado)
                
                if account_updates:
                    account_query = f"UPDATE user_account SET {', '.join(account_updates)} WHERE id_user = %s"
                    account_params.append(id_user)
                    cur.execute(account_query, account_params)
            
            conn.commit()
            
            # Obtener usuario actualizado
            query = """
                SELECT 
                    ua.id_user,
                    ua.email,
                    ua.id_role,
                    ua.state,
                    up.first_name,
                    up.last_name,
                    up.phone
                FROM user_account ua
                LEFT JOIN user_profile up ON ua.id_user = up.id_user
                WHERE ua.id_user = %s
            """
            
            cur.execute(query, (id_user,))
            usuario_actualizado = cur.fetchone()
            usuario_mapped = _map_usuario(usuario_actualizado)
            cur.close()
            
            logger.info(f"Usuario actualizado: ID {id_user}")
            return build_response(
                success=True,
                data=usuario_mapped,
                message="Usuario actualizado exitosamente",
                code=200
            )
            
    except MySQLError as e:
        logger.error(f"Error MySQL al actualizar usuario {id_user}: {str(e)}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar usuario {id_user}: {str(e)}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.delete("/{id_user}", response_model=dict)
async def eliminar_usuario(id_user: int):
    """
    Desactiva un usuario (soft delete - no elimina de la BD, solo marca como inactivo).
    
    **Parámetros:**
    - id_user: ID del usuario a desactivar
    
    **Respuesta:**
    - success (bool): Indica si la operación fue exitosa
    - data: Información del usuario desactivado
    """
    try:
        with get_conn() as conn:
            cur = conn.cursor(dictionary=True)
            
            # Verificar que el usuario existe
            cur.execute(
                """
                SELECT id_user, email
                FROM user_account
                WHERE id_user = %s
                """,
                (id_user,)
            )
            usuario = cur.fetchone()
            
            if not usuario:
                logger.warning(f"Intento de eliminar usuario no existente: ID {id_user}")
                raise HTTPException(status_code=404, detail=f"Usuario con ID {id_user} no encontrado")
            
            # Soft delete: marcar como inactivo
            cur.execute(
                "UPDATE user_account SET state = FALSE WHERE id_user = %s",
                (id_user,)
            )
            
            conn.commit()
            logger.info(f"Usuario desactivado: {usuario['email']} (ID: {id_user})")
            
            # Obtener el usuario desactivado con todos sus datos para mapeo
            query = """
                SELECT 
                    ua.id_user,
                    ua.email,
                    ua.id_role,
                    ua.state,
                    up.first_name,
                    up.last_name,
                    up.phone
                FROM user_account ua
                LEFT JOIN user_profile up ON ua.id_user = up.id_user
                WHERE ua.id_user = %s
            """
            
            cur.execute(query, (id_user,))
            usuario_full = cur.fetchone()
            usuario_mapped = _map_usuario(usuario_full)
            cur.close()
            
            return build_response(
                success=True,
                data=usuario_mapped,
                message="Usuario eliminado exitosamente",
                code=200
            )
            
    except MySQLError as e:
        logger.error(f"Error MySQL al eliminar usuario {id_user}: {str(e)}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar usuario {id_user}: {str(e)}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")