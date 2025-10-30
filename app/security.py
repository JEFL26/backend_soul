# backend/app/security.py
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from . import config
from .core import user_logic

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración para JWT
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Obtiene el usuario actual basado en el token JWT.
    
    Args:
        credentials (HTTPAuthorizationCredentials): Credenciales de autorización.
    
    Returns:
        dict: Información del usuario actual.
    
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, config.settings.SECRET_KEY, algorithms=[config.settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = user_logic.get_user_by_email(email)
    if user is None:
        raise credentials_exception
    
    return {
        "email": user["email"],
        "role": user["id_role"],
        "user_id": user["id_user"]
    }

def get_password_hash(password: str) -> str:
    """
    Genera un hash de la contraseña proporcionada.

    Args:
        password (str): Contraseña en texto plano.

    Returns:
        str: Hash de la contraseña.
    """
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash.

    Args:
        plain (str): Contraseña en texto plano.
        hashed (str): Hash de la contraseña.

    Returns:
        bool: True si la contraseña coincide, False en caso contrario.
    """
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Crea un token de acceso JWT.

    Args:
        data (dict): Datos a incluir en el token.
        expires_delta (timedelta | None): Tiempo de expiración del token.

    Returns:
        str: Token JWT codificado.

    Raises:
        Exception: Si hay un error al crear el token.
    """
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + (
            expires_delta if expires_delta 
            else timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, config.settings.SECRET_KEY, algorithm=config.settings.ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise Exception(f"Error al crear el token de acceso: {str(e)}")