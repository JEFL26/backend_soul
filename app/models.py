# backend/app/models.py
from pydantic import BaseModel, EmailStr
from typing import Optional

# Modelos de usuarios
class UserCreate(BaseModel):
    """
    Modelo para crear un nuevo usuario con perfil.

    Attributes:
        email (EmailStr): Correo electrónico del usuario.
        password (str): Contraseña del usuario.
        first_name (str): Nombre del usuario.
        last_name (str): Apellido del usuario.
        phone (str): Número de teléfono del usuario.
        id_role (int): ID del rol del usuario (por defecto 2, usuario normal).
    """
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str
    id_role: int = 2  # Por defecto, asumimos que es un usuario normal

class UserLogin(BaseModel):
    """
    Modelo para el inicio de sesión del usuario.

    Attributes:
        email (EmailStr): Correo electrónico del usuario.
        password (str): Contraseña del usuario.
    """
    email: EmailStr
    password: str

class UserOut(BaseModel):
    """
    Modelo para la respuesta de información del usuario.

    Attributes:
        id_user (int): ID del usuario.
        email (EmailStr): Correo electrónico del usuario.
        first_name (Optional[str]): Nombre del usuario.
        last_name (Optional[str]): Apellido del usuario.
        phone (Optional[str]): Número de teléfono del usuario.
        id_role (int): ID del rol del usuario.
        state (bool): Estado del usuario (activo/inactivo).
    """
    id_user: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    id_role: int
    state: bool

class UserUpdate(BaseModel):
    """
    Modelo para actualizar un usuario.

    Attributes:
        email (Optional[EmailStr]): Correo electrónico del usuario.
        first_name (Optional[str]): Nombre del usuario.
        last_name (Optional[str]): Apellido del usuario.
        phone (Optional[str]): Número de teléfono del usuario.
        id_role (Optional[int]): ID del rol del usuario.
    """
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    id_role: Optional[int] = None

class Token(BaseModel):
    """
    Modelo para el token de autenticación.

    Attributes:
        access_token (str): Token de acceso.
        token_type (str): Tipo de token (por defecto "bearer").
    """
    access_token: str
    token_type: str = "bearer"

# Modelos de servicios
class ServiceBase(BaseModel):
    """
    Modelo base para servicios.

    Attributes:
        name (str): Nombre del servicio.
        description (Optional[str]): Descripción del servicio.
        duration_minutes (int): Duración del servicio en minutos.
        price (float): Precio del servicio.
        state (bool): Estado del servicio (activo/inactivo).
    """
    name: str
    description: Optional[str] = None
    duration_minutes: int
    price: float
    state: bool = True

class ServiceOut(ServiceBase):
    """
    Modelo para la respuesta de información del servicio.

    Attributes:
        id_service (int): ID del servicio.
    """
    id_service: int

# Modelos de reservas
class ReservationCreate(BaseModel):
    """
    Modelo para crear una nueva reserva.

    Attributes:
        id_service (int): ID del servicio a reservar.
        start_datetime (str): Fecha y hora de inicio de la reserva (formato: YYYY-MM-DD HH:MM:SS).
        end_datetime (str): Fecha y hora de finalización de la reserva (formato: YYYY-MM-DD HH:MM:SS).
        payment_method (str): Método de pago (Efectivo, Tarjeta, Transferencia).
    """
    id_service: int
    start_datetime: str
    end_datetime: str
    payment_method: str

class ReservationOut(BaseModel):
    """
    Modelo para la respuesta de información de la reserva.

    Attributes:
        id_reservation (int): ID de la reserva.
        id_user (int): ID del usuario que hizo la reserva.
        id_service (int): ID del servicio reservado.
        id_reservation_status (int): ID del estado de la reserva.
        start_datetime (str): Fecha y hora de inicio de la reserva.
        end_datetime (str): Fecha y hora de finalización de la reserva.
        created_at (str): Fecha de creación de la reserva.
        total_price (float): Precio total de la reserva.
        payment_method (str): Método de pago.
        state (bool): Estado de la reserva.
        service_name (Optional[str]): Nombre del servicio.
        status_name (Optional[str]): Nombre del estado de la reserva.
        service_description (Optional[str]): Descripción del servicio.
        duration_minutes (Optional[int]): Duración del servicio en minutos.
    """
    id_reservation: int
    id_user: int
    id_service: int
    id_reservation_status: int
    start_datetime: str
    end_datetime: str
    created_at: str
    total_price: float
    payment_method: str
    state: bool
    service_name: Optional[str] = None
    status_name: Optional[str] = None
    service_description: Optional[str] = None
    duration_minutes: Optional[int] = None
    first_name: Optional[str] = None        
    last_name: Optional[str] = None         
    email: Optional[str] = None 

# Modelos para administración de usuarios
class UsuarioUpdate(BaseModel):
    """
    Modelo para actualizar un usuario (mapeado desde frontend).
    Acepta campos del frontend y los traduce a backend_soul.
    
    Attributes:
        nombre_completo (Optional[str]): Nombre completo del usuario.
        telefono (Optional[str]): Teléfono del usuario.
        rol (Optional[str]): Rol del usuario (Cliente, Estilista, Admin).
        estado (Optional[bool]): Estado del usuario (activo/inactivo).
    """
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None
    rol: Optional[str] = None
    estado: Optional[bool] = None

class UsuarioListOut(BaseModel):
    """
    Modelo para la respuesta de listado de usuarios.
    
    Attributes:
        id_user (int): ID del usuario.
        email (EmailStr): Correo del usuario.
        first_name (Optional[str]): Nombre del usuario.
        last_name (Optional[str]): Apellido del usuario.
        phone (Optional[str]): Teléfono del usuario.
        id_role (int): ID del rol.
        state (bool): Estado del usuario.
    """
    id_user: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    id_role: int
    state: bool