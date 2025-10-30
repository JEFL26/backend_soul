# backend/app/core/logic_upload_excel.py
import pandas as pd
import time
import logging
from typing import Dict, Any, Callable, Optional
from ..database import get_conn
from app.utils.responses import build_response
import asyncio
from io import BytesIO
import base64
import json

EXPECTED_COLUMNS = {"name", "description", "duration_minutes", "price", "state"}


# ======================================================
# Limpia las tablas temporales de una sesión específica
# ======================================================
def clear_temp_tables(user_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM data_imported WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM data_errors WHERE user_id = %s", (user_id,))
            conn.commit()
        finally:
            cur.close()


# ======================================================
# Procesa el archivo Excel (multi-hoja)
# ======================================================
async def process_excel_async(
    file_content: bytes,
    filename: str,
    start_time: float,
    user_id: int,
    max_time: int = 180,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Dict[str, Any]:
    results = {
        "filename": filename,
        "valid_sheets": [],
        "invalid_sheets": [],
        "errors": [],
        "total_rows": 0,
    }

    try:
        # Leer todas las hojas del Excel
        excel_data = pd.read_excel(BytesIO(file_content), sheet_name=None, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo {filename}: {str(e)}")

    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)

        for sheet_name, df in excel_data.items():
            try:
                df = df.fillna("")

                missing_cols = EXPECTED_COLUMNS - set(df.columns)
                if missing_cols:
                    results["invalid_sheets"].append(sheet_name)
                    cur.execute(
                        """INSERT INTO data_errors (sheet_name, row_num, error_message, user_id)
                           VALUES (%s, %s, %s, %s)""",
                        (
                            sheet_name,
                            0,
                            f"Estructura inválida: faltan columnas {', '.join(missing_cols)}",
                            user_id,
                        ),
                    )
                    conn.commit()
                    continue

                results["valid_sheets"].append(sheet_name)
                total_rows = len(df)
                results["total_rows"] += total_rows

                for idx, row in df.iterrows():
                    row_num = idx + 2

                    # Validación básica
                    name = str(row.get("name", "")).strip()
                    if not name:
                        cur.execute(
                            """INSERT INTO data_errors (sheet_name, row_num, error_message, user_id)
                               VALUES (%s, %s, %s, %s)""",
                            (sheet_name, row_num, "Nombre vacío", user_id),
                        )
                        conn.commit()
                        continue

                    try:
                        duration = int(row["duration_minutes"])
                        price = float(row["price"])
                        state = bool(int(row["state"]) if str(row["state"]).isdigit() else row["state"])

                        if duration <= 0:
                            raise ValueError("Duración inválida")
                        if price < 0:
                            raise ValueError("Precio negativo")

                        # Guardar fila válida en tabla temporal
                        cur.execute(
                            """INSERT INTO data_imported (sheet_name, name, description, duration_minutes, price, state, user_id)
                               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (
                                sheet_name,
                                name,
                                str(row.get("description", "")).strip() or None,
                                duration,
                                price,
                                state,
                                user_id,
                            ),
                        )
                        conn.commit()

                    except ValueError as ve:
                        conn.rollback()
                        cur.execute(
                            """INSERT INTO data_errors (sheet_name, row_num, error_message, user_id)
                               VALUES (%s, %s, %s, %s)""",
                            (sheet_name, row_num, str(ve), user_id),
                        )
                        conn.commit()
                    except Exception as e:
                        conn.rollback()
                        cur.execute(
                            """INSERT INTO data_errors (sheet_name, row_num, error_message, user_id)
                               VALUES (%s, %s, %s, %s)""",
                            (sheet_name, row_num, f"Error inesperado: {str(e)}", user_id),
                        )
                        conn.commit()

                    # Emitir progreso
                    if progress_callback:
                        percent = ((idx + 1) / total_rows) * 100
                        progress_callback(percent)
                        await asyncio.sleep(0.001)

                    if time.time() - start_time > max_time:
                        raise TimeoutError(f"Tiempo máximo {max_time}s excedido.")

            except Exception as e:
                logging.exception(f"Error procesando hoja {sheet_name}")
                cur.execute(
                    """INSERT INTO data_errors (sheet_name, row_num, error_message, user_id)
                       VALUES (%s, %s, %s, %s)""",
                    (sheet_name, 0, f"Error procesando hoja: {str(e)}", user_id),
                )
                conn.commit()
                results["invalid_sheets"].append(sheet_name)

        cur.close()

    return results

async def handle_excel_upload_ws(user_id: int, files: list, websocket, start_time: float):
    summary = {"total_files": 0, "total_rows": 0}
    results = []
    clear_temp_tables(user_id)

    for f in files:
        filename = f.get("filename")
        try:
            content_bytes = base64.b64decode(f.get("content"))
        except Exception:
            await websocket.send_text(json.dumps(build_response(False, f"Archivo inválido: {filename}", None, 400).body.decode()))
            continue

        await websocket.send_text(json.dumps({
            "event": "start_file",
            "filename": filename,
            "progress": 0
        }))

        def progress_callback(percent: float):
            import asyncio
            asyncio.create_task(websocket.send_text(json.dumps({
                "event": "progress",
                "filename": filename,
                "progress": round(percent, 2)
            })))


        file_result = await process_excel_async(
            content_bytes,
            filename,
            start_time,
            user_id,
            progress_callback=progress_callback
        )

        results.append(file_result)
        summary["total_files"] += 1
        summary["total_rows"] += file_result["total_rows"]

        await websocket.send_text(json.dumps({
            "event": "preview_ready",
            "filename": filename,
            "valid_sheets": file_result["valid_sheets"],
            "invalid_sheets": file_result["invalid_sheets"]
        }))

    return {"summary": summary, "details": results}


def get_uploaded_sheets_by_user(user_id: int):
    """
    Obtiene las hojas cargadas con sus datos y errores organizados por hoja.
    
    Returns:
        {
            "sheets": {
                "Hoja1": {
                    "data": [...],
                    "errors": [...],
                    "stats": {
                        "total_rows": 10,
                        "error_count": 2
                    }
                }
            },
            "summary": {
                "total_sheets": 2,
                "total_rows": 15,
                "total_errors": 3
            }
        }
    """
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        
        # Obtener hojas distintas
        cur.execute("SELECT DISTINCT sheet_name FROM data_imported WHERE user_id = %s", (user_id,))
        sheets = [r["sheet_name"] for r in cur.fetchall()]

        result = {}
        total_rows = 0
        total_errors = 0
        
        for sheet in sheets:
            # Datos de la hoja
            cur.execute(
                "SELECT * FROM data_imported WHERE user_id = %s AND sheet_name = %s",
                (user_id, sheet)
            )
            sheet_data = cur.fetchall()
            
            # Errores de la hoja
            cur.execute(
                "SELECT * FROM data_errors WHERE user_id = %s AND sheet_name = %s",
                (user_id, sheet)
            )
            sheet_errors = cur.fetchall()
            
            row_count = len(sheet_data)
            error_count = len(sheet_errors)
            
            result[sheet] = {
                "data": sheet_data,
                "errors": sheet_errors,
                "stats": {
                    "total_rows": row_count,
                    "error_count": error_count
                }
            }
            
            total_rows += row_count
            total_errors += error_count
        
        # Buscar errores de hojas inválidas (sin datos)
        cur.execute(
            """SELECT DISTINCT sheet_name FROM data_errors 
               WHERE user_id = %s AND sheet_name NOT IN (
                   SELECT DISTINCT sheet_name FROM data_imported WHERE user_id = %s
               )""",
            (user_id, user_id)
        )
        invalid_sheets = [r["sheet_name"] for r in cur.fetchall()]
        
        for sheet in invalid_sheets:
            cur.execute(
                "SELECT * FROM data_errors WHERE user_id = %s AND sheet_name = %s",
                (user_id, sheet)
            )
            sheet_errors = cur.fetchall()
            
            result[sheet] = {
                "data": [],
                "errors": sheet_errors,
                "stats": {
                    "total_rows": 0,
                    "error_count": len(sheet_errors)
                }
            }
            total_errors += len(sheet_errors)
        
        cur.close()

    return {
        "sheets": result,
        "summary": {
            "total_sheets": len(sheets),
            "total_rows": total_rows,
            "total_errors": total_errors,
            "has_invalid_sheets": len(invalid_sheets) > 0
        }
    }


# ======================================================
# Actualizar un registro específico en data_imported
# ======================================================
def update_imported_row(user_id: int, id_import: int, updates: dict) -> tuple[bool, str]:
    """
    Actualiza un registro en data_imported.
    
    Args:
        user_id: ID del usuario (para validar propiedad)
        id_import: ID del registro a actualizar
        updates: Diccionario con los campos a actualizar
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validar que solo se actualicen campos permitidos
    allowed_fields = {"name", "description", "duration_minutes", "price", "state"}
    invalid_fields = set(updates.keys()) - allowed_fields
    
    if invalid_fields:
        return False, f"Campos no permitidos: {', '.join(invalid_fields)}"
    
    # Validaciones de negocio
    if "name" in updates:
        name = str(updates["name"]).strip()
        if not name:
            return False, "El nombre no puede estar vacío"
        updates["name"] = name
    
    if "duration_minutes" in updates:
        try:
            duration = int(updates["duration_minutes"])
            if duration <= 0:
                return False, "La duración debe ser mayor a 0"
            updates["duration_minutes"] = duration
        except (ValueError, TypeError):
            return False, "Duración inválida"
    
    if "price" in updates:
        try:
            price = float(updates["price"])
            if price < 0:
                return False, "El precio no puede ser negativo"
            updates["price"] = price
        except (ValueError, TypeError):
            return False, "Precio inválido"
    
    if "state" in updates:
        try:
            state = bool(int(updates["state"]) if str(updates["state"]).isdigit() else updates["state"])
            updates["state"] = state
        except (ValueError, TypeError):
            return False, "Estado inválido"
    
    if "description" in updates:
        desc = str(updates["description"]).strip()
        updates["description"] = desc if desc else None
    
    # Construir query dinámicamente
    if not updates:
        return False, "No hay campos para actualizar"
    
    set_clause = ", ".join([f"{field} = %s" for field in updates.keys()])
    values = list(updates.values())
    values.extend([user_id, id_import])
    
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            # Verificar que el registro existe y pertenece al usuario
            cur.execute(
                "SELECT id_import FROM data_imported WHERE id_import = %s AND user_id = %s",
                (id_import, user_id)
            )
            if not cur.fetchone():
                return False, "Registro no encontrado o no autorizado"
            
            # Actualizar
            query = f"UPDATE data_imported SET {set_clause} WHERE user_id = %s AND id_import = %s"
            cur.execute(query, values)
            conn.commit()
            
            if cur.rowcount == 0:
                return False, "No se pudo actualizar el registro"
            
            return True, "Registro actualizado exitosamente"
            
        except Exception as e:
            conn.rollback()
            logging.exception("Error actualizando registro importado")
            return False, f"Error al actualizar: {str(e)}"
        finally:
            cur.close()

# ======================================================
# Cancelar/eliminar previsualización del usuario
# ======================================================
def cancel_user_preview(user_id: int) -> tuple[bool, str, dict]:
    """
    Elimina todos los datos temporales (importados y errores) de un usuario específico.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        tuple: (success: bool, message: str, stats: dict)
    """
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            # Contar registros antes de eliminar
            cur.execute("SELECT COUNT(*) as count FROM data_imported WHERE user_id = %s", (user_id,))
            imported_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM data_errors WHERE user_id = %s", (user_id,))
            errors_count = cur.fetchone()['count']
            
            # Eliminar datos importados
            cur.execute("DELETE FROM data_imported WHERE user_id = %s", (user_id,))
            deleted_imported = cur.rowcount
            
            # Eliminar errores
            cur.execute("DELETE FROM data_errors WHERE user_id = %s", (user_id,))
            deleted_errors = cur.rowcount
            
            conn.commit()
            
            stats = {
                "deleted_rows": deleted_imported,
                "deleted_errors": deleted_errors,
                "total_deleted": deleted_imported + deleted_errors
            }
            
            if deleted_imported == 0 and deleted_errors == 0:
                return True, "No había datos para eliminar", stats
            
            return True, f"Previsualización cancelada: {deleted_imported} registros eliminados", stats
            
        except Exception as e:
            conn.rollback()
            logging.exception("Error cancelando previsualización")
            return False, f"Error al cancelar previsualización: {str(e)}", {}
        finally:
            cur.close()

# ======================================================
# Confirmar e insertar datos en la tabla service
# ======================================================
async def confirm_import_to_service(user_id: int, selected_sheets: list[str], websocket) -> dict:
    """
    Inserta registros de data_imported a service y limpia tablas temporales.
    Envía progreso en tiempo real por WebSocket.
    
    Args:
        user_id: ID del usuario
        selected_sheets: Lista de nombres de hojas a confirmar
        websocket: Conexión WebSocket para enviar progreso
    
    Returns:
        dict con estadísticas de la operación
    """
    stats = {
        "total_processed": 0,
        "inserted": 0,
        "duplicated": 0,
        "failed": 0,
        "errors": []
    }
    
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        
        try:
            # Obtener todos los registros de las hojas seleccionadas
            placeholders = ', '.join(['%s'] * len(selected_sheets))
            query = f"""
                SELECT * FROM data_imported 
                WHERE user_id = %s AND sheet_name IN ({placeholders})
                ORDER BY sheet_name, id_import
            """
            cur.execute(query, [user_id] + selected_sheets)
            records = cur.fetchall()
            
            total_records = len(records)
            
            if total_records == 0:
                return {
                    **stats,
                    "message": "No hay registros para confirmar en las hojas seleccionadas"
                }
            
            # Enviar inicio
            await websocket.send_text(json.dumps({
                "event": "start_confirmation",
                "total_records": total_records,
                "selected_sheets": selected_sheets
            }))
            
            # Procesar cada registro
            for idx, record in enumerate(records, 1):
                try:
                    # Verificar si ya existe el servicio por nombre
                    cur.execute("SELECT id_service FROM service WHERE name = %s", (record['name'],))
                    existing = cur.fetchone()
                    
                    if existing:
                        stats["duplicated"] += 1
                        await websocket.send_text(json.dumps({
                            "event": "progress",
                            "current": idx,
                            "total": total_records,
                            "progress": round((idx / total_records) * 100, 2),
                            "status": "duplicated",
                            "name": record['name']
                        }))
                        continue
                    
                    # Insertar en service
                    cur.execute(
                        """INSERT INTO service (name, description, duration_minutes, price, state)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (
                            record['name'],
                            record['description'],
                            record['duration_minutes'],
                            record['price'],
                            record['state']
                        )
                    )
                    conn.commit()
                    stats["inserted"] += 1
                    
                    # Enviar progreso
                    await websocket.send_text(json.dumps({
                        "event": "progress",
                        "current": idx,
                        "total": total_records,
                        "progress": round((idx / total_records) * 100, 2),
                        "status": "inserted",
                        "name": record['name']
                    }))
                    
                except Exception as e:
                    conn.rollback()
                    stats["failed"] += 1
                    error_msg = f"Error insertando '{record['name']}': {str(e)}"
                    stats["errors"].append(error_msg)
                    logging.error(error_msg)
                    
                    await websocket.send_text(json.dumps({
                        "event": "progress",
                        "current": idx,
                        "total": total_records,
                        "progress": round((idx / total_records) * 100, 2),
                        "status": "failed",
                        "name": record['name'],
                        "error": str(e)
                    }))
                
                stats["total_processed"] += 1
                
                # Pequeña pausa para no saturar
                await asyncio.sleep(0.01)
            
            # Limpiar tablas temporales del usuario
            cur.execute("DELETE FROM data_imported WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM data_errors WHERE user_id = %s", (user_id,))
            conn.commit()
            
            # Enviar completado
            await websocket.send_text(json.dumps({
                "event": "completed",
                "stats": stats
            }))
            
        except Exception as e:
            conn.rollback()
            logging.exception("Error confirmando importación")
            raise
        finally:
            cur.close()
    
    return stats