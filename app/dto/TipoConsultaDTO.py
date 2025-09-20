from pydantic import BaseModel, Field
from datetime import datetime

class TipoConsultaBase(BaseModel):
    nome: str = Field(..., max_length=100)
    descricao: str | None = None
    duracao_padrao_minutos: int = Field(..., gt=0, description="Duração deve ser maior que zero.")

class TipoConsultaCreate(TipoConsultaBase):
    pass

class TipoConsultaUpdate(BaseModel):
    nome: str | None = Field(default=None, max_length=100)
    descricao: str | None = None
    duracao_padrao_minutos: int | None = Field(default=None, gt=0, description="Duração deve ser maior que zero.")

class TipoConsultaRead(TipoConsultaBase):
    codtipoconsulta: int
    data_criacao: datetime
    data_atualizacao: datetime

    class Config:
        from_attributes = True 