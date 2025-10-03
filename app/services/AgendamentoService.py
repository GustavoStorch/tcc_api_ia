from sqlalchemy.orm import Session
from datetime import timedelta

from ..repository.AgendamentoRepository import agendamento_repo
from ..models import AgendamentoModel, ProfissionalModel, TipoConsultaModel, ValorConsultaModal, PacienteModel
from ..dto import AgendamentoDTO
from . import GoogleCalendarService

def criar_novo_agendamento(db: Session, agendamento_data: AgendamentoDTO.AgendamentoCreate) -> AgendamentoModel.Agendamento:
    # Busca as informações de Profissional, Tipo de Consulta e Valor da Consulta.
   
    paciente = db.query(PacienteModel.Paciente).filter(PacienteModel.Paciente.nome == agendamento_data.nomepaciente).first()
    profissional = db.query(ProfissionalModel.Profissional).filter(ProfissionalModel.Profissional.nome == agendamento_data.nomeprofissional).first()
    tipoConsulta = db.query(TipoConsultaModel.TipoConsulta).filter(TipoConsultaModel.TipoConsulta.nome == agendamento_data.nometipoconsulta).first()
    # profissional = db.query(ProfissionalModel.Profissional).filter(ProfissionalModel.Profissional.codprofissional == agendamento_data.codprofissional).first()
    # tipoConsulta = db.query(TipoConsultaModel.TipoConsulta).filter(TipoConsultaModel.TipoConsulta.codtipoconsulta == agendamento_data.codtipoconsulta).first() 
    
    if not paciente:
        raise ValueError("Paciente não encontrado.")
    if not profissional:
        raise ValueError("Profissional não encontrado.")
    if not tipoConsulta:
        raise ValueError("Tipo de Consulta não encontrado.")
    
    valor_consulta = db.query(ValorConsultaModal.ValorConsulta)\
    .filter(ValorConsultaModal.ValorConsulta.codprofissional == profissional.codprofissional)\
    .filter(ValorConsultaModal.ValorConsulta.codtipoconsulta == tipoConsulta.codtipoconsulta)\
    .first()

    if not valor_consulta:
        raise ValueError("Valor da COnsulta não encontrado.")

    # Calcular horário do fim da consulta
    horario_fim = agendamento_data.horario_inicio + timedelta(minutes=tipoConsulta.duracao_padrao_minutos)

    # Criação da instância do modelo SQLAlchemy
    db_agendamento = AgendamentoModel.Agendamento(
        codpaciente=paciente.codpaciente,
        codprofissional=profissional.codprofissional,
        codtipoconsulta=tipoConsulta.codtipoconsulta,
        codclinica=agendamento_data.codclinica,
        horario_inicio=agendamento_data.horario_inicio,
        horario_fim=horario_fim,
        valor_cobrado=valor_consulta.valor
    )

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
        print(f"ATENÇÃO: Agendamento {novo_agendamento_db.codagendamento} salvo no DB, mas falhou ao criar no Google Calendar. Erro: {e}")

    return novo_agendamento_db