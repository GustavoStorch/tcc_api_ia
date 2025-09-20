from sqlalchemy.orm import Session
from ..models.AgendamentoModel import Agendamento
from ..dto.AgendamentoDTO import AgendamentoCreate

class AgendamentoRepository:
    def criar_agendamento(self, db: Session, agendamento: Agendamento) -> Agendamento:
        """
        Adiciona uma nova instância de Agendamento (já construída) ao banco de dados,
        faz o commit e atualiza o objeto com os dados do DB (como o ID gerado).
        """
        db.add(agendamento)
        db.commit()
        db.refresh(agendamento)
        return agendamento

agendamento_repo = AgendamentoRepository()