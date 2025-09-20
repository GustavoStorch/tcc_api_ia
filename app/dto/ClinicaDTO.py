from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.models.ClinicaModel import TipoSituacaoClinica

class ClinicaBase(BaseModel):
    nome_fantasia: str | None = None
    cnpj: str
    email: EmailStr  
    telefone: str | None = None
    cep: str | None = None
    pais: str
    estado: str
    cidade: str
    bairro: str
    rua: str
    numero: str
    complemento: str | None = None

class ClinicaCreate(ClinicaBase):
    pass

class ClinicaUpdate(BaseModel):
    nome_fantasia: str | None = None
    cnpj: str | None = None
    email: EmailStr | None = None
    telefone: str | None = None
    cep: str | None = None
    pais: str | None = None
    estado: str | None = None
    cidade: str | None = None
    bairro: str | None = None
    rua: str | None = None
    numero: str | None = None
    complemento: str | None = None
    situacao: TipoSituacaoClinica | None = None

class ClinicaRead(ClinicaBase):
    codclinica: int
    situacao: TipoSituacaoClinica
    data_criacao: datetime
    data_atualizacao: datetime

    class Config:
        from_attributes = True 