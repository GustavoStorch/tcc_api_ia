
from fastapi import APIRouter, Depends

from app.models import UsuarioModel
from app.dto.UsuarioDTO import UsuarioDTO as user_schema
from app.api.deps import get_current_user

router = APIRouter()

# Define rota que busca o usuário do banco de dados
@router.get("/me", response_model=user_schema)
def read_users_me(current_user: UsuarioModel.Usuario = Depends(get_current_user)):
    return current_user