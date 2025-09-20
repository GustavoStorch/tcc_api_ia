from sqlalchemy.orm import Session
from datetime import timedelta

from ..repository.AgendamentoRepository import agendamento_repo
from ..models import AgendamentoModel, ProfissionalModel, TipoConsultaModel, ValorConsultaModal 
from ..dto import AgendamentoDTO
from . import GoogleCalendarService

def criar_novo_agendamento(db: Session, agendamento_data: AgendamentoDTO.AgendamentoCreate) -> AgendamentoModel.Agendamento:
    # Busca as informações de Profissional, Tipo de Consulta e Valor da Consulta.
    profissional = db.query(ProfissionalModel.Profissional).filter(ProfissionalModel.Profissional.codprofissional == agendamento_data.codprofissional).first()
    tipoConsulta = db.query(TipoConsultaModel.TipoConsulta).filter(TipoConsultaModel.TipoConsulta.codtipoconsulta == agendamento_data.codtipoconsulta).first() 
    valor_consulta = db.query(ValorConsultaModal.ValorConsulta)\
    .filter(ValorConsultaModal.ValorConsulta.codprofissional == agendamento_data.codprofissional)\
    .filter(ValorConsultaModal.ValorConsulta.codtipoconsulta == agendamento_data.codtipoconsulta)\
    .first()
    
    if not profissional:
        raise ValueError("Profissional não encontrado.")
    if not tipoConsulta:
        raise ValueError("Tipo de Consulta não encontrado.")
    if not valor_consulta:
        raise ValueError("Valor da COnsulta não encontrado.")

    # Calcular horário do fim da consulta
    horario_fim = agendamento_data.horario_inicio + timedelta(minutes=tipoConsulta.duracao_padrao_minutos)

    dados_para_db = agendamento_data.model_dump() 
    dados_para_db['horario_fim'] = horario_fim
    dados_para_db['valor_cobrado'] = valor_consulta.valor

    # Criação da instância do modelo SQLAlchemy
    db_agendamento = AgendamentoModel.Agendamento(**dados_para_db)

    novo_agendamento_db = agendamento_repo.criar_agendamento(
        db=db, 
        agendamento=db_agendamento
    )

    # Integra o agendamento no Google calendário.
    try:
        summary = f"Consulta: {profissional.nome}"
        description = f"Agendamento via API da Clínica. Tipo de Consulta ID: {agendamento_data.codtipoconsulta}"
        
        GoogleCalendarService.create_calendar_event(
            summary=summary,
            start_time=novo_agendamento_db.horario_inicio.isoformat(),
            end_time=novo_agendamento_db.horario_fim.isoformat(),
            description=description
        )
    except Exception as e:
        #Avaliar para tratar como Pendente de Integração no google calendário caso dê erro.
        print(f"ATENÇÃO: Agendamento {novo_agendamento_db.codagendamento} salvo no DB, mas falhou ao criar no Google Calendar. Erro: {e}")

    return novo_agendamento_db