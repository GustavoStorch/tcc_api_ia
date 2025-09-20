from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from ..models.PacienteModel import TipoSituacaoPaciente

class PacienteBase(BaseModel):
    nome: str
    cpf: str = Field(..., description="CPF no formato XXX.XXX.XXX-XX")
    telefone: str
    email: EmailStr | None = None
    telegram_chat_id: int | None = None
    cep: str | None = None
    rua: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None

class PacienteCreate(PacienteBase):
    pass

class PacienteUpdate(BaseModel):
    nome: str | None = None
    cpf: str | None = None
    telefone: str | None = None
    email: EmailStr | None = None
    telegram_chat_id: int | None = None
    cep: str | None = None
    rua: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    situacao: TipoSituacaoPaciente | None = None

class PacienteRead(PacienteBase):
    codpaciente: int
    situacao: TipoSituacaoPaciente
    data_criacao: datetime
    data_atualizacao: datetime

    class Config:
        from_attributes = True 