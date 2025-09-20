from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.models.ProfissionalModel import TipoSituacaoProfissional

class ProfissionalBase(BaseModel):
    nome: str
    crm: str
    especialidade: str
    email: EmailStr | None = None 
    telefone: str | None = None

class ProfissionalCreate(ProfissionalBase):
    pass

class ProfissionalUpdate(BaseModel):
    nome: str | None = None
    crm: str | None = None
    especialidade: str | None = None
    email: EmailStr | None = None
    telefone: str | None = None
    situacao: TipoSituacaoProfissional | None = None

class ProfissionalRead(ProfissionalBase):
    codprofissional: int
    situacao: TipoSituacaoProfissional
    data_criacao: datetime
    data_atualizacao: datetime

    class Config:
        from_attributes = True 