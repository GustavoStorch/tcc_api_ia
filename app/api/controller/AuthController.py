from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.repository.UsuarioRepository import user_repo
from app.dto.TokenDTO import TokenDTO
from app.core import security
from app.models.base import get_db

router = APIRouter()

# Define a rota de login e cobra ele a ter o token
@router.post("/login", response_model=TokenDTO)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
   # Busca o usuário do banco de dados
    user = user_repo.get_user_by_username(db, username=form_data.username)
    
    # Valida a senha do banco de dados com a senha digitada
    if not user or not security.verify_password(form_data.password, user.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-A             uthenticate": "Bearer"},
        )
    
    # Definição do tempo de expiração do token que será gerado
    access_token_expires = timedelta(minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    #Cria o Token de acesso
    access_token = security.create_access_token(
        data={"sub": user.usuario}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}