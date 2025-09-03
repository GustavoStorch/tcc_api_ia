from pydantic import BaseModel, EmailStr
from ..models.UsuarioModel import TipoFuncaoUsuario, TipoSituacaoUsuario

class UsuarioDTO(BaseModel):
    id: int
    nome: str
    usuario: str
    email: EmailStr
    funcao: TipoFuncaoUsuario
    situacao: TipoSituacaoUsuario

    class Config:
        from_attributes = True