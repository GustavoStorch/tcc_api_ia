from pydantic import BaseModel
from datetime import datetime

class LembretePendenteResponse(BaseModel):
    nome_paciente: str
    telegram_chat_id: int
    nome_profissional: str
    horario_inicio: datetime
    dias_restantes: int

    class Config:
        from_attributes = True