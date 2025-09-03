from pydantic import BaseModel
from datetime import datetime

class AgendamentoCreate(BaseModel):
    paciente_id: int
    profissional_id: int
    tipo_consulta_id: int
    clinica_id: int
    horario_inicio: datetime 

class AgendamentoRead(BaseModel):
    id: int
    paciente_id: int
    profissional_id: int
    horario_inicio: datetime
    horario_fim: datetime
    valor_cobrado: float
    situacao: str

    class Config:
        from_attributes = True #