from pydantic import BaseModel
from datetime import datetime

class AgendamentoCreate(BaseModel):
    codpaciente: int
    codprofissional: int
    codtipoconsulta: int
    codclinica: int
    horario_inicio: datetime 

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