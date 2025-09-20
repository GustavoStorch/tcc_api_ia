from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

from .ProfissionalDTO import ProfissionalRead
from .TipoConsultaDTO import TipoConsultaRead

class ValorConsultaBase(BaseModel):
    codprofissional: int
    codtipoconsulta: int
    valor: Decimal = Field(..., gt=0, decimal_places=2, description="Valor da consulta, deve ser positivo.")

class ValorConsultaCreate(ValorConsultaBase):
    pass

class ValorConsultaUpdate(BaseModel):
    valor: Decimal = Field(..., gt=0, decimal_places=2, description="Novo valor da consulta.")

class ValorConsultaRead(ValorConsultaBase):
    codvalorconsulta: int
    data_criacao: datetime
    data_atualizacao: datetime
    
    profissional: ProfissionalRead
    tipo_consulta: TipoConsultaRead

    class Config:
        from_attributes = True 