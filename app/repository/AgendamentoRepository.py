from sqlalchemy.orm import Session
from sqlalchemy import func, case
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
    
    def get_historico_paciente(self, db: Session, codpaciente: int) -> dict:
        historico = db.query(
            func.count(Agendamento.codagendamento).label('total'),
            func.sum(case((Agendamento.situacao.in_(['Nao Compareceu', 'Cancelado Pelo Paciente']), 1), else_=0)).label('no_shows')
        ).filter(
            Agendamento.codpaciente == codpaciente,
            Agendamento.situacao.in_(['Concluido', 'Nao Compareceu', 'Cancelado Pelo Paciente'])
        ).first()

        total_agendamentos = historico.total if historico and historico.total else 0
        total_no_shows = historico.no_shows if historico and historico.no_shows else 0
        
        taxa = (total_no_shows / total_agendamentos) if total_agendamentos > 0 else 0.0

        return {
            "historico_agendamentos": total_agendamentos,
            "historico_no_shows": total_no_shows,
            "taxa_no_show": taxa
        }

agendamento_repo = AgendamentoRepository()