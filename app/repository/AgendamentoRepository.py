from sqlalchemy.orm import Session
from ..models.AgendamentoModel import Agendamento
from ..dto.AgendamentoDTO import AgendamentoCreate

class AgendamentoRepository:
    def criar_agendamento(self, db: Session, agendamento: Agendamento) -> Agendamento:
        # Salva no banco e commita para o banco o novo agendamento.
        db.add(agendamento)
        db.commit()
        db.refresh(agendamento)
        return agendamento

agendamento_repo = AgendamentoRepository()