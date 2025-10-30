# backend/app/rutas/auth.py
from fastapi import APIRouter
from datetime import timedelta
from ..core import user_logic
from ..security import create_access_token
from ..config import settings
from ..models import UserCreate, UserOut, UserLogin
from app.utils.responses import ok, bad_request, server_error
import logging

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register")
def register(data: UserCreate):
    """
    Crea un nuevo usuario si el email no existe.
    
    Args:
        data (UserCreate): Datos del usuario a crear.
    
    Returns:
        JSONResponse: Respuesta uniforme con éxito o error.
    """
    try:
        user = user_logic.get_user_by_email(data.email)
        if user:
            return bad_request("Email already registered")

        new_user = user_logic.create_user(data)
        return ok("User created successfully", UserOut(**new_user).dict())

    except Exception as e:
        logging.exception("Error creating user")
        return server_error(f"Error creating user: {str(e)}")


@router.post("/login")
def login(data: UserLogin):
    """
    Autentica usuario y genera token JWT.
    
    Args:
        data (UserLogin): Credenciales del usuario.
    
    Returns:
        JSONResponse: Token JWT o error en formato uniforme.
    """
    try:
        user = user_logic.authenticate_user(data.email, data.password)
        if not user:
            return bad_request("Invalid credentials")

        token = create_access_token(
            {"sub": user["email"], "role": user["id_role"]},
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return ok("Login successful", {"access_token": token, "token_type": "bearer"})

    except Exception as e:
        logging.exception("Login error")
        return server_error(f"Login error: {str(e)}")
