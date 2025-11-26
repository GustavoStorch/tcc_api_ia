from sqlalchemy.orm import Session
from datetime import timedelta

from ..repository.AgendamentoRepository import agendamento_repo
from ..models import AgendamentoModel, ProfissionalModel, TipoConsultaModel, PacienteModel, ValorConsultaModel
from ..dto import AgendamentoDTO, PredicaoDTO
from . import GoogleCalendarService
from zoneinfo import ZoneInfo
from datetime import datetime
from ..services.PredicaoService import prediction_service

def criar_novo_agendamento(db: Session, agendamento_data: AgendamentoDTO.AgendamentoCreate) -> AgendamentoModel.Agendamento:
    # Busca as informações de Profissional, Tipo de Consulta e Valor da Consulta.
    paciente = db.query(PacienteModel.Paciente).filter(PacienteModel.Paciente.nome == agendamento_data.nomepaciente).first()
    profissional = db.query(ProfissionalModel.Profissional).filter(ProfissionalModel.Profissional.nome == agendamento_data.nomeprofissional).first()
    tipoConsulta = db.query(TipoConsultaModel.TipoConsulta).filter(TipoConsultaModel.TipoConsulta.nome == agendamento_data.nometipoconsulta).first()
    
    if not paciente:
        raise ValueError("Paciente não encontrado.")
    if not profissional:
        raise ValueError("Profissional não encontrado.")
    if not tipoConsulta:
        raise ValueError("Tipo de Consulta não encontrado.")
    
    valor_consulta = db.query(ValorConsultaModel.ValorConsulta)\
    .filter(ValorConsultaModel.ValorConsulta.codprofissional == profissional.codprofissional)\
    .filter(ValorConsultaModel.ValorConsulta.codtipoconsulta == tipoConsulta.codtipoconsulta)\
    .first()

    if not valor_consulta:
        raise ValueError("Valor da COnsulta não encontrado.")

    # Realiza as conversões de horas conforme fuso horários dos pacients.
    clinic_tz = ZoneInfo('America/Sao_Paulo')
    patient_tz_str = paciente.fuso_horario if paciente.fuso_horario else 'America/Sao_Paulo'
    patient_tz = ZoneInfo(patient_tz_str)

    naive_patient_start_time = agendamento_data.horario_inicio
    patient_aware_start_time = naive_patient_start_time.replace(tzinfo=patient_tz)
    duration = timedelta(minutes=tipoConsulta.duracao_padrao_minutos)
    patient_aware_end_time = patient_aware_start_time + duration

    clinic_aware_start_time = patient_aware_start_time.astimezone(clinic_tz)
    clinic_aware_end_time = patient_aware_end_time.astimezone(clinic_tz)

    # naive_start_time = agendamento_data.horario_inicio
    # aware_start_time = naive_start_time.replace(tzinfo=clinic_tz)
    # aware_end_time = aware_start_time + timedelta(minutes=tipoConsulta.duracao_padrao_minutos)
    db_agendamento = AgendamentoModel.Agendamento(
        codpaciente=paciente.codpaciente,
        codprofissional=profissional.codprofissional,
        codtipoconsulta=tipoConsulta.codtipoconsulta,
        codclinica=agendamento_data.codclinica,
        horario_inicio=clinic_aware_start_time,
        horario_fim=clinic_aware_end_time,
        valor_cobrado=valor_consulta.valor
    )

    stats_paciente = agendamento_repo.get_historico_paciente(db, paciente.codpaciente)

    feature_predicao = PredicaoDTO.PredictionFeatures(
        antecedencia_dias=(clinic_aware_start_time.date() - datetime.now().date()).days,
        dia_da_semana=clinic_aware_start_time.weekday(),
        mes=clinic_aware_start_time.month,
        hora_do_dia=clinic_aware_start_time.hour,
        historico_no_shows=stats_paciente["historico_no_shows"], 
        historico_agendamentos=stats_paciente["historico_agendamentos"],
        taxa_no_show=stats_paciente["taxa_no_show"]
    )

    # feature_predicao = PredicaoDTO.PredictionFeatures(
    #     antecedencia_dias=(clinic_aware_start_time.date() - datetime.now().date()).days,
    #     dia_da_semana=clinic_aware_start_time.weekday(),
    #     mes=clinic_aware_start_time.month,
    #     hora_do_dia=clinic_aware_start_time.hour,
    #     historico_no_shows=0, 
    #     historico_agendamentos=0,
    #     taxa_no_show=0.0
    # )

    resultado_predicao = prediction_service.predict(feature_predicao)

    db_agendamento.probabilidade_no_show = resultado_predicao["probabilidade_no_show"]
    db_agendamento.risco = resultado_predicao["risco"]

    novo_agendamento_db = agendamento_repo.criar_agendamento(
        db=db,  
        agendamento=db_agendamento
    )

    # Integra o agendamento no Google calendário.
    try:
        summary = f"Consulta: {profissional.nome}"
        description = f"Agendamento via API da Clínica. Tipo de Consulta: {agendamento_data.nometipoconsulta}"

        event_id_clinica = GoogleCalendarService.create_calendar_event(
            summary=summary,
            start_time=clinic_aware_start_time.isoformat(),
            end_time=clinic_aware_end_time.isoformat(),
            description=description
        )

    except Exception as e:
        print(f"ATENÇÃO: Agendamento {novo_agendamento_db.codagendamento} salvo no DB, mas falhou ao criar no Google Calendar da Clínica. Erro: {e}")

    if paciente.token:
        try:
            print(f"Paciente {paciente.nome} tem um token. A tentar criar evento no seu calendário pessoal.")
            
            event_id_paciente = GoogleCalendarService.create_patient_calendar_event(
                refresh_token=paciente.token, 
                summary=f"Consulta com {profissional.nome}",
                start_time=patient_aware_start_time.isoformat(),
                end_time=patient_aware_end_time.isoformat(),
                timeZone=paciente.fuso_horario,
                description=f"Agendamento na clínica. Tipo: {tipoConsulta.nome}"
            )
            print("Evento criado com sucesso no calendário do paciente.")
        except Exception as e:
            print(f"AVISO: Não foi possível criar o evento no calendário pessoal do paciente. Erro: {e}") 

    try:
        novo_agendamento_db = agendamento_repo.create_calendar_event(
        db=db,  
        agendamento=novo_agendamento_db,
        codAgendaClinica = event_id_clinica,
        codAgendaPaciente = event_id_paciente
    )
    except Exception as e:
        print(f"Erro ao salvar IDs do Google Calendar no agendamento: {e}")
        db.rollback()
        

    return novo_agendamento_db