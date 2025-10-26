from sqlalchemy.orm import Session
from ..models.AgendamentoModel import Agendamento, TipoSituacaoAgendamento
from ..dto.AgendamentoDTO import AgendamentoCreate
from datetime import datetime

class AgendamentoRepository:
    def criar_agendamento(self, db: Session, agendamento: Agendamento) -> Agendamento:
        # Salva no banco e commita para o banco o novo agendamento.
        db.add(agendamento)
        db.commit()
        db.refresh(agendamento)
        return agendamento

    def update_risco_agendamento(self, db: Session, agendamento: Agendamento, probabilidade: float, risco: str) -> Agendamento:
        agendamento.probabilidade_no_show = probabilidade
        agendamento.risco = risco
        db.commit()
        db.refresh(agendamento)
        return agendamento

    def get_proximo_agendamento_pendente(self, db: Session, codpaciente: int) -> Agendamento | None:
        return db.query(Agendamento)\
            .filter(
                Agendamento.codpaciente == codpaciente,
                Agendamento.situacao.in_(['Agendado', 'Confirmado']),
                Agendamento.horario_inicio > datetime.now()
            )\
            .order_by(Agendamento.horario_inicio.asc())\
            .first()
    
    def get_by_id(self, db: Session, codAgendamento: int) -> Agendamento | None:
        return db.query(Agendamento)\
            .filter(
                Agendamento.codagendamento == codAgendamento,
                Agendamento.situacao.in_(['Agendado', 'Confirmado'])
            )\
            .order_by(Agendamento.horario_inicio.asc())\
            .first()
    
    def update_status_agendamento(self, db: Session, agendamento: Agendamento, novo_status: TipoSituacaoAgendamento) -> Agendamento:
        agendamento.situacao = novo_status
        db.commit()
        db.refresh(agendamento)
        return agendamento
    
    def create_calendar_event(self, db: Session, agendamento: Agendamento, codAgendaClinica: str, codAgendaPaciente: str) -> Agendamento:
        agendamento.codagendaclinica = codAgendaClinica
        agendamento.codagendapaciente = codAgendaPaciente
        db.commit()
        db.refresh(agendamento)
        return agendamento

agendamento_repo = AgendamentoRepository()