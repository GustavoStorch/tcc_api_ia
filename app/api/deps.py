from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from pydantic import ValidationError

from app.models.base import get_db
from app.repository.UsuarioRepository import user_repo
from app.models import UsuarioModel
from app.core import security
from app.dto.TokenDTO import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> UsuarioModel.Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decodificação do token JWT a partir da chave secreta e recupera o usuário
        payload = security.jwt.decode(
            token, security.settings.SECRET_KEY, algorithms=[security.settings.ALGORITHM]
        )
        
        # Valida se o Token é valido ou não, isso com base na propriedade usuário
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    # Realiza a validação para caso o usuário ainda tenha sido deletado após o login
    user = user_repo.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
        
    return user