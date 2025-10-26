from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AgendamentoCreate(BaseModel):
    nomepaciente: str
    nomeprofissional: str
    nometipoconsulta: str
    codclinica: int
    horario_inicio: datetime 
    codagendaclinica: Optional[str] = None
    codagendapaciente: Optional[str] = None

class AgendamentoRead(BaseModel):
    codagendamento: int
    codpaciente: int 
    codprofissional: int
    horario_inicio: datetime
    horario_fim: datetime
    valor_cobrado: float
    situacao: str

    class Config:
        from_attributes = True 