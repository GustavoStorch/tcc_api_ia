from sqlalchemy.orm import Session
from sqlalchemy import func
import google.generativeai as genai
from pinecone import Pinecone
from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo
import json
import httpx
import pytz

from ..core.config import settings
from ..models import AgendamentoModel, GradeHorariosModel
from ..repository.ProfissionalRepository import profissional_repo
from ..repository.PacienteRepository import paciente_repo 
from ..repository.AgendamentoRepository import agendamento_repo
from ..services.SincronizacaoVetorialService import embedder
from ..models.PacienteModel import Paciente
from ..dto.AgendamentoDTO import AgendamentoCreate
from ..services.AgendamentoService import criar_novo_agendamento
from ..services.GoogleCalendarService import esta_ocupado_google_calendar
from . import GoogleCalendarService
from ..core.RedisClient import redis_client

# Inicializa o Pinecone e o Gemini
try:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
    intent_model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"Erro ao inicializar serviços de IA: {e}")
    pinecone_index = None
    intent_model = None

# Identifica a intenção da mensagem usando o gemini
def _get_intent_and_entities(query: str) -> dict:
    today = date.today().strftime('%Y-%m-%d')
    prompt = f"""
    Analise a pergunta do utilizador e classifique a sua intenção.
    As intenções possíveis são: 'saudacao', 'confirmar_agendamento', 'criar_agendamento', 'consulta_horarios', 'cancelar_agendamento', 'modificar_agendamento', 'informacao_geral', 'resposta_localizacao'.

    - 'saudacao' é para cumprimentos gerais como "Oi", "Bom dia", "Tudo bem?".
    - 'confirmar_agendamento' é usado para respostas como "Sim", "Confirmo", "Ok, confirmado".
    - 'criar_agendamento' é usado quando o utilizador pede explicitamente para marcar uma consulta.
    - 'consulta_horarios' é para quando o utilizador pergunta sobre horários livres.
    - 'cancelar_agendamento': O utilizador quer cancelar uma consulta. (Ex: "Quero cancelar meu agendamento", "Preciso desmarcar minha consulta")
    - 'modificar_agendamento': O utilizador quer mudar a data/hora de uma consulta. (Ex: "Quero reagendar minha consulta", "Posso trocar o horário?")
    - 'informacao_geral' é para todas as outras perguntas.
    - 'resposta_localizacao': A resposta do utilizador a uma pergunta sobre a sua localização.

    Se a intenção for 'criar_agendamento' ou 'consulta_horarios', extraia o nome do profissional e a data desejada (no formato AAAA-MM-DD).
    Se a intenção for 'criar_agendamento', extraia também a hora (no formato HH:MM).
    Considere que a data de hoje é {today}.
    Exemplos de datas relativas: 'amanhã' deve ser { (date.today() + timedelta(days=1)).strftime('%Y-%m-%d') }, 'depois de amanhã' deve ser { (date.today() + timedelta(days=2)).strftime('%Y-%m-%d') }.

    A sua resposta DEVE ser apenas um objeto JSON válido.

    Exemplo 1:
    Pergunta: "Quais os horários da Dra. Ana para amanhã?"
    Resposta: {{"intent": "consulta_horarios", "entities": {{"nome_profissional": "Dra. Ana", "data": "{(date.today() + timedelta(days=1)).strftime('%Y-%m-%d')}"}}}}

    Exemplo 2:
    Pergunta: "Qual o CRM do Dr. Carlos?"
    Resposta: {{"intent": "informacao_geral", "entities": {{}}}}

    Exemplo 3:
    Pergunta: "Gostaria de marcar uma consulta com o Dr. Ricardo Mendes para sexta-feira às 15:30."
    Resposta: {{"intent": "criar_agendamento", "entities": {{"nome_profissional": "Dr. Ricardo Mendes", "data": "2025-10-10", "hora": "15:30"}}}}
    
    Exemplo 4:
    Pergunta: "Sim, confirmo a minha presença."
    Resposta: {{"intent": "confirmar_agendamento", "entities": {{}}}}

    Exemplo 5:
    Pergunta: "Bom dia, tudo bem?"
    Resposta: {{"intent": "saudacao", "entities": {{}}}}

    Exemplo 6:
    Pergunta: "Não, agora moro em Curitiba, Paraná."
    Resposta: {{"intent": "resposta_localizacao", "entities": {{"confirmacao": "nao", "nova_localizacao": "Curitiba, Paraná"}}}}

    Exemplo 7:
    Pergunta: "Sim, está correto minha localização."
    Resposta: {{"intent": "resposta_localizacao", "entities": {{"confirmacao": "sim", "localizacao_atual": "Curitiba, Paraná"}}}}

    Exemplo 8:
    Pergunta: "Gostaria de cancelar minha consulta de sexta."
    Respuesta: {{"intent": "cancelar_agendamento", "entities": {{"data": "2025-10-10"}}}}

    Exemplo 9:
    Pergunta: "Preciso reagendar meu horário com a Dra. Ana"
    Respuesta: {{"intent": "modificar_agendamento", "entities": {{"nome_profissional": "Dra. Ana"}}}}

    Pergunta do Utilizador: "{query}"
    """
    response = intent_model.generate_content(prompt)
    try:
        # Limpa a resposta para garantir que seja um JSON válido
        clean_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean_response)
    except (json.JSONDecodeError, AttributeError):
        return {"intent": "informacao_geral", "entities": {}}

def _handle_schedule_query(entities: dict, db: Session) -> dict:
    nome_profissional = entities.get("nome_profissional")
    data_str = entities.get("data")

    if not nome_profissional or not data_str:
        return {"answer": "Para consultar os horários, preciso saber o nome do profissional e a data. Pode me informar, por favor?", "context": []}

    profissional = profissional_repo.get_profissional_by_name(db, nome=nome_profissional)
    if not profissional:
        return {"answer": f"Não encontrei um profissional com o nome {nome_profissional}. Pode verificar o nome?", "context": []}

    try:
        data = date.fromisoformat(data_str)
    except ValueError:
        return {"answer": f"A data '{data_str}' não parece estar num formato válido (AAAA-MM-DD). Pode tentar novamente?", "context": []}
        
    dias_semana_map = {0: "Segunda", 1: "Terca", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sabado", 6: "Domingo"}
    dia_semana_str = dias_semana_map.get(data.weekday())
    
    grade_do_dia = db.query(GradeHorariosModel.GradeHorarios).filter(
        GradeHorariosModel.GradeHorarios.codprofissional == profissional.codprofissional, 
        GradeHorariosModel.GradeHorarios.dia == dia_semana_str
    ).first()
    
    if not grade_do_dia:
        return {"answer": f"O(A) {profissional.nome} não atende neste dia da semana ({dia_semana_str}).", "context": []}

    try:
        fuso_horario = pytz.timezone('America/Sao_Paulo') 
    except pytz.UnknownTimeZoneError:
        fuso_horario = pytz.UTC

    inicio_dia_local = fuso_horario.localize(datetime.combine(data, time.min))
    fim_dia_local = fuso_horario.localize(datetime.combine(data, time.max))

    agendamentos_ocupados = db.query(AgendamentoModel.Agendamento.horario_inicio).filter(
        AgendamentoModel.Agendamento.codprofissional == profissional.codprofissional, 
        AgendamentoModel.Agendamento.horario_inicio >= inicio_dia_local,
        AgendamentoModel.Agendamento.horario_inicio <= fim_dia_local
    ).all()
    
    horarios_ocupados = set()
    for ag in agendamentos_ocupados:
        hora_local = ag.horario_inicio.astimezone(fuso_horario)
        horarios_ocupados.add(hora_local.time().replace(tzinfo=None))
    
    todos_os_slots = set()
    duracao_consulta = timedelta(minutes=60) 
    
    turnos = []
    if grade_do_dia.horainciomanha and grade_do_dia.horafimmanha:
        turnos.append((grade_do_dia.horainciomanha, grade_do_dia.horafimmanha))
        
    if grade_do_dia.horainciotarde and grade_do_dia.horafimtarde:
        turnos.append((grade_do_dia.horainciotarde, grade_do_dia.horafimtarde))
        
    if grade_do_dia.horaincionoite and grade_do_dia.horafimnoite:
        turnos.append((grade_do_dia.horaincionoite, grade_do_dia.horafimnoite))
        
    if not turnos:
        return {"answer": f"O(A) {profissional.nome} não parece ter um horário de trabalho configurado para este dia.", "context": []}
    
    for inicio_turno, fim_turno in turnos:
        slot_atual = datetime.combine(data, inicio_turno)
        fim_turno_dt = datetime.combine(data, fim_turno)
        
        while slot_atual + duracao_consulta <= fim_turno_dt:
            todos_os_slots.add(slot_atual.time())
            slot_atual += duracao_consulta
            
    horarios_disponiveis = sorted(list(todos_os_slots - horarios_ocupados))
    
    if not horarios_disponiveis:
        data_formatada = data.strftime('%d/%m/%Y')
        return {"answer": f"Não há horários disponíveis para {profissional.nome} na data {data_formatada}.", "context": []}

    data_formatada = data.strftime('%d/%m/%Y')
    resposta_formatada = f"Os horários disponíveis para {profissional.nome} no dia {data_formatada} são: {', '.join([t.strftime('%H:%M') for t in horarios_disponiveis])}."
    return {"answer": resposta_formatada, "context": []}



# Processamento utilizando a pipeline RAG
def _handle_rag_query(query: str) -> dict:
    # query_embedding_result = genai.embed_content(model="models/embedding-001", content=query)
    # query_vector = query_embedding_result['embedding']
    query_vector = embedder.encode([query], convert_to_numpy=True)[0].tolist()
    query_results = pinecone_index.query(vector=query_vector, top_k=5, include_metadata=True)
    context_list = [match['metadata']['texto'] for match in query_results['matches']]
    context_str = "\n- ".join(context_list)
    prompt = f"""
    Você é um assistente virtual de uma clínica médica.
    Baseado estritamente no CONTEXTO abaixo, responda à PERGUNTA do utilizador.
    Se a resposta não estiver no contexto, diga que não encontrou essa informação.
    CONTEXTO:
    - {context_str}
    PERGUNTA:
    {query}
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    return {"answer": response.text, "context": context_list}

# Valida token do usuário e solicita sua permissão caso não tiver ainda.
def _handle_create_appointment(entities: dict, telegram_id: int, db: Session, query: str, intent: str) -> dict:
    paciente = paciente_repo.get_by_telegram_id(db, telegram_id=telegram_id)
    if not paciente:
        return {"answer": "Não consegui encontrar o seu registo de paciente.", "context": []}

    if not paciente.token:
        auth_link = f"http://127.0.0.1:8000/auth/google/login?telegramid={telegram_id}"
        return {
            "answer": "Para adicionar o agendamento ao seu Google Calendar, preciso da sua permissão. Por favor, clique no link abaixo para autorizar.",
            "context": [],
            "action_type": "REQUER_AUTORIZACAO_GCAL",
            "action_data": {"type": "REQUER_AUTORIZACAO_GCAL", "original_intent_data": {"query": query, "intent": intent, "entities": entities}}
        }

    nome_profissional = entities.get("nome_profissional")
    data_str = entities.get("data")
    hora_str = entities.get("hora")
    tipo_consulta = entities.get("tipo_consulta", "Primeira Consulta")

    if not all([nome_profissional, data_str, hora_str]):
        return {"answer": "Faltam informações para o agendamento (profissional, data ou hora).", "context": []}

    try:
        fuso_horario_clinica = pytz.timezone('America/Sao_Paulo')
        horario_inicio_dt = datetime.fromisoformat(f"{data_str}T{hora_str}:00")
        horario_inicio_aware = fuso_horario_clinica.localize(horario_inicio_dt)
        
        agendamento_para_criar = AgendamentoCreate(
            nomepaciente=paciente.nome,
            nomeprofissional=nome_profissional,
            nometipoconsulta=tipo_consulta,
            codclinica=1,
            horario_inicio=horario_inicio_aware
        )

        novo_agendamento = criar_novo_agendamento(db=db, agendamento_data=agendamento_para_criar)

        try:
            fuso_paciente = pytz.timezone(paciente.fuso_horario) if paciente.fuso_horario else fuso_horario_clinica
        except:
            fuso_paciente = fuso_horario_clinica

        horario_inicio_paciente = novo_agendamento.horario_inicio.astimezone(fuso_paciente)
        data_formatada = horario_inicio_paciente.strftime('%d/%m/%Y às %H:%M')

        # data_formatada = novo_agendamento.horario_inicio.strftime('%d/%m/%Y às %H:%M')
        return {
            "answer": f"Pronto! O seu agendamento com {novo_agendamento.profissional.nome} foi confirmado para o dia {data_formatada}.",
            "context": [],
            "action_type": None,
            "action_data": None
        }

    except ValueError as e: 
        return {"answer": f"Não foi possível agendar: {str(e)}", "context": []}
    except Exception as e: 
        print(f"ERRO INESPERADO ao criar agendamento: {e}")
        return {"answer": "Peço desculpa, ocorreu um erro inesperado ao tentar criar o seu agendamento.", "context": []}

# Realiza a confirmação do agendamento conforme envio de lembrete enviado ao paciente.
def _handle_confirmation(telegram_id: int, db: Session) -> dict:
    paciente = paciente_repo.get_by_telegram_id(db, telegram_id=telegram_id)
    if not paciente:
        return {"answer": "Não consegui encontrar o seu registo para confirmar a consulta."}

    proximo_agendamento = agendamento_repo.get_proximo_agendamento_pendente(db, codpaciente=paciente.codpaciente)

    if not proximo_agendamento:
        return {"answer": "Obrigado pela resposta! No momento, não encontrei agendamentos pendentes para confirmar.", "context": [], "action_type": None, "action_data": None}
    
    agendamento_repo.update_status_agendamento(db, agendamento=proximo_agendamento, novo_status="Confirmado")
    
    data_formatada = proximo_agendamento.horario_inicio.strftime('%d/%m/%Y às %H:%M')
    return {"answer": f"Obrigado por confirmar! O seu agendamento para o dia {data_formatada} está confirmado.", "context": [], "action_type": None, "action_data": None}

# Busca o fuso horário conforme a localização passada pelo paciente.
def _inferir_fuso_horario_de_local(local: str) -> str | None:
    prompt = f"""
    Com base na localização fornecida, retorne o nome do fuso horário padrão do banco de dados IANA (timezone database).
    Responda apenas com o nome do fuso horário e nada mais. A sua resposta deve ser no formato Continente/Cidade.

    Exemplos:
    Localização: "São Paulo"
    Resposta: America/Sao_Paulo

    Localização: "Estou em Lisboa, Portugal"
    Resposta: Europe/Lisbon

    Localização: "Orlando, Flórida"
    Resposta: America/New_York

    Localização: "Manaus"
    Resposta: America/Manaus
    
    Localização: "Tóquio"
    Resposta: Asia/Tokyo

    Localização do Utilizador: "{local}"
    """
    try:
        if not intent_model:
            raise ConnectionError("Modelo de IA para inferência de fuso horário não inicializado.")
            
        response = intent_model.generate_content(prompt)
        fuso_horario = response.text.strip()
        
        if "/" in fuso_horario and not " " in fuso_horario:
            print(f"DEBUG: Fuso horário inferido para '{local}': {fuso_horario}")
            return fuso_horario
        else:
            print(f"DEBUG: Resposta do Gemini para fuso horário não está no formato esperado: {fuso_horario}")
            return None
    except Exception as e:
        print(f"Erro ao inferir fuso horário: {e}")
        return None
    
# Retorna a mensagem padrão da clinica.
def _handle_greeting(query: str) -> dict:
    return {"answer": "Olá! Bem vindo à nossa clinica. Como posso ajudar?", "context": [], "action_type": None, "action_data": None}

# Atualiza fuso horário do cliente no banco de dados e chama o chat novamente.
def _handle_localization_response(query: str, db: Session, paciente: Paciente, action_context: dict) -> dict:
    original_intent_data = action_context.get("original_intent_data", {})
    confirmacao = action_context.get("confirmacao")

    if confirmacao == "sim":
        return {
            "answer": "Entendido. Obrigado por confirmar!", 
            "context": [], 
            "action_type": None, 
            "action_data": None
        }

    fuso_inferido = _inferir_fuso_horario_de_local(query)
    if fuso_inferido:
        paciente_repo.update_fuso_horario(db, paciente=paciente, fuso_horario=fuso_inferido)
        return process_chat_query(original_intent_data.get("query"), str(paciente.telegram_chat_id), db, action_context=None)
    else:
        return {
            "answer": "Peço desculpa, não consegui identificar um fuso horário para essa localização. Pode tentar novamente com 'cidade, estado'?", 
            "context": [], 
            "action_type": "REQUER_LOCALIZACAO", 
            "action_data": action_context
        }

# Realiza o cancelamento do agendamento
def _perform_cancellation(db: Session, paciente: Paciente, agendamento: AgendamentoModel.Agendamento) -> bool:
    try:
        agendamento_repo.update_status_agendamento(db, agendamento=agendamento, novo_status=AgendamentoModel.TipoSituacaoAgendamento.Cancelado_Pelo_Paciente)
        
        try:
            GoogleCalendarService.delete_calendar_event(event_id=agendamento.codagendaclinica)
        except Exception as e:
            print(f"AVISO: Não foi possível deletar evento do calendário da CLÍNICA. Erro: {e}")

        # 3. Deleta o evento do calendário do Paciente (se ele deu permissão)
        if paciente.token:
            try:
                GoogleCalendarService.delete_patient_calendar_event(event_id=agendamento.codagendapaciente, refresh_token=paciente.token)
            except Exception as e:
                print(f"AVISO: Não foi possível deletar evento do calendário do PACIENTE. Erro: {e}")

        return True
    except Exception as e:
        print(f"ERRO ao executar cancelamento: {e}")
        return False

#Busca o agendamento a ser cancelado
def _handle_cancel_request(telegram_id: int, db: Session) -> dict:
    paciente = paciente_repo.get_by_telegram_id(db, telegram_id=telegram_id)
    if not paciente:
        return {"answer": "Não encontrei seu registro de paciente.", "context": []}

    proximo_agendamento = agendamento_repo.get_proximo_agendamento_pendente(db, codpaciente=paciente.codpaciente) 
    
    if not proximo_agendamento:
        return {"answer": "Você não possui agendamentos futuros para cancelar.", "context": [], "action_type": None, "action_data": None}

    try:
        patient_tz = ZoneInfo(paciente.fuso_horario if paciente.fuso_horario else 'America/Sao_Paulo')
        horario_paciente = proximo_agendamento.horario_inicio.astimezone(patient_tz)
        data_formatada = horario_paciente.strftime('%d/%m/%Y às %H:%M')
    except Exception:
        data_formatada = proximo_agendamento.horario_inicio.strftime('%d/%m/%Y às %H:%M (Horário da Clínica)')

    return {
        "answer": f"Encontrei um agendamento com {proximo_agendamento.profissional.nome} para o dia {data_formatada}. Você confirma o CANCELAMENTO deste horário? (Responda 'sim' ou 'não')",
        "context": [],
        "action_type": "REQUER_CONFIRMACAO_CANCELAMENTO",
        "action_data": {
            "type": "AGUARDANDO_CONFIRMACAO_CANCELAMENTO",
            "codagendamento": proximo_agendamento.codagendamento
        }
    }

#Busca o agendamento a ser modificado
def _handle_reschedule_request(telegram_id: int, db: Session) -> dict:
    paciente = paciente_repo.get_by_telegram_id(db, telegram_id=telegram_id)
    if not paciente:
        return {"answer": "Não encontrei seu registro de paciente.", "context": []}

    proximo_agendamento = agendamento_repo.get_proximo_agendamento_pendente(db, codpaciente=paciente.codpaciente) 
    
    if not proximo_agendamento:
        return {"answer": "Você não possui agendamentos futuros para reagendar.", "context": [], "action_type": None, "action_data": None}

    try:
        patient_tz = ZoneInfo(paciente.fuso_horario if paciente.fuso_horario else 'America/Sao_Paulo')
        horario_paciente = proximo_agendamento.horario_inicio.astimezone(patient_tz)
        data_formatada = horario_paciente.strftime('%d/%m/%Y às %H:%M')
    except Exception:
        data_formatada = proximo_agendamento.horario_inicio.strftime('%d/%m/%Y às %H:%M (Horário da Clínica)')

    return {
        "answer": f"Entendido. Para reagendar, primeiro precisamos cancelar sua consulta atual com {proximo_agendamento.profissional.nome} no dia {data_formatada}. Você confirma o cancelamento para prosseguir com o REAGENDAMENTO? (Responda 'sim' ou 'não')",
        "context": [],
        "action_type": "REQUER_CONFIRMACAO_REAGENDAMENTO",
        "action_data": {
            "type": "AGUARDANDO_CONFIRMACAO_REAGENDAMENTO",
            "codagendamento": proximo_agendamento.codagendamento
        }
    }

DIAS_SEMANA_PY_MAP = {0: "Segunda", 1: "Terca", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sabado", 6: "Domingo"}

def _get_paciente_horario_preferido(db: Session, codpaciente: int, fuso_horario_paciente: str) -> time | None:
    try:
        # Query para extrair hora e minuto do horário ajustado ao fuso
        query = db.query(
            func.extract('hour', AgendamentoModel.Agendamento.horario_inicio).label('hora'),
            func.extract('minute', AgendamentoModel.Agendamento.horario_inicio).label('minuto'),
            func.count().label('total')
        ).filter(
            AgendamentoModel.Agendamento.codpaciente == codpaciente,
            AgendamentoModel.Agendamento.situacao.in_([
                AgendamentoModel.TipoSituacaoAgendamento.Concluido,
                AgendamentoModel.TipoSituacaoAgendamento.Confirmado,
                AgendamentoModel.TipoSituacaoAgendamento.Agendado
            ])
        ).group_by('hora', 'minuto') \
        .order_by(func.count().desc()) \
        .limit(1)

        resultado = query.first()
        if resultado:
            hora_obj = (datetime.combine(date.today(), time(int(resultado.hora), int(resultado.minuto))) 
                 - timedelta(hours=3)).time()
            print(f"DEBUG: Horário preferido encontrado para {codpaciente}: {hora_obj}")
            return hora_obj

    except Exception as e:
        print(f"Erro ao buscar horário preferido: {e}")

    return None


def _encontrar_proxima_data_disponivel(db: Session, nome_profissional: str, horario_preferido: time) -> date | None:
    hoje = date.today()
    for i in range(1, 30):  # procura pelos próximos 30 dias
        data_teste = hoje + timedelta(days=i)
        if _verificar_disponibilidade(db, nome_profissional, data_teste, horario_preferido):
            return data_teste
    return None


def _verificar_disponibilidade(db: Session, nome_profissional: str, data: date, hora: time) -> bool:
    try:
        profissional = profissional_repo.get_profissional_by_name(db, nome=nome_profissional)
        if not profissional:
            return False

        dia_semana_str = DIAS_SEMANA_PY_MAP.get(data.weekday())
        grade_do_dia = db.query(GradeHorariosModel.GradeHorarios).filter(
            GradeHorariosModel.GradeHorarios.codprofissional == profissional.codprofissional,
            GradeHorariosModel.GradeHorarios.dia == dia_semana_str
        ).first()

        if not grade_do_dia:
            return False

        fuso_horario_clinica = pytz.timezone('America/Sao_Paulo')
        slot_dt_naive = datetime.combine(data, hora)
        slot_dt_aware = fuso_horario_clinica.localize(slot_dt_naive)

        # Verifica se dentro de algum turno
        turnos = []
        if grade_do_dia.horainciomanha and grade_do_dia.horafimmanha:
            turnos.append((grade_do_dia.horainciomanha, grade_do_dia.horafimmanha))
        if grade_do_dia.horainciotarde and grade_do_dia.horafimtarde:
            turnos.append((grade_do_dia.horainciotarde, grade_do_dia.horafimtarde))
        if grade_do_dia.horaincionoite and grade_do_dia.horafimnoite:
            turnos.append((grade_do_dia.horaincionoite, grade_do_dia.horafimnoite))

        horario_na_grade = any(inicio <= hora < fim for inicio, fim in turnos)
        if not horario_na_grade:
            return False

        # Verifica se já existe agendamento
        agendamento_ocupado = db.query(AgendamentoModel.Agendamento).filter(
            AgendamentoModel.Agendamento.codprofissional == profissional.codprofissional,
            AgendamentoModel.Agendamento.horario_inicio == slot_dt_aware,
            AgendamentoModel.Agendamento.situacao.in_(['Agendado', 'Confirmado', 'Concluido'])
        ).first()

        if esta_ocupado_google_calendar(nome_profissional, data, hora):
            return False

        return agendamento_ocupado is None

    except Exception as e:
        print(f"Erro ao verificar disponibilidade: {e}")
        return False
    
def process_chat_query(query: str, session_id: str, db: Session, action_context: dict | None = None) -> dict:
    
    # ETAPA 0: Carregar o contexto da "memória"
    session_key = f"chat_session:{session_id}"
    action_context = None
    location_confirmed_this_run = False
    
    if redis_client:
        try:
            context_json = redis_client.get(session_key)
            if context_json:
                action_context = json.loads(context_json)
                print(f"DEBUG: Contexto carregado para {session_id}: {action_context}")
        except Exception as e:
            print(f"Erro ao LER contexto do Redis: {e}")
    else:
        print("AVISO: Redis client não está disponível.")

    try:
        telegram_id = int(session_id)
    except (ValueError, TypeError):
        return {"answer": "ID de sessão inválido.", "context": [], "action_type": None, "action_data": None}

    paciente = paciente_repo.get_by_telegram_id(db, telegram_id=telegram_id)
    if not paciente:
        return {"answer": "Não consegui encontrar o seu registo de paciente.", "context": [], "action_type": None, "action_data": None}

    # ETAPA 1: Gerir o estado da conversa, se possui algo na memória
    if action_context:
        context_type = action_context.get("type")
        original_intent_data = action_context.get("original_intent_data", {})

        if context_type == "AGUARDANDO_LOCALIZACAO":
            fuso_inferido = _inferir_fuso_horario_de_local(query)
            if fuso_inferido:
                paciente_repo.update_fuso_horario(db, paciente=paciente, fuso_horario=fuso_inferido)

                _registrar_confirmacao_hoje(telegram_id)

                query = original_intent_data.get("query")
                action_context = None 
                location_confirmed_this_run = True
            else:
                response = {"answer": "Peço desculpa, não consegui identificar um fuso horário para essa localização. Pode tentar novamente?", "context": [], "action_type": "REQUER_LOCALIZACAO", "action_data": action_context}
                if redis_client:
                    redis_client.set(session_key, json.dumps(response.get("action_data")))
                    redis_client.expire(session_key, 900) # 15 minutos
                return response

        elif context_type == "AGUARDANDO_CONFIRMACAO_LOCALIZACAO":
            if "sim" in query.lower() or "correto" in query.lower():
                _registrar_confirmacao_hoje(telegram_id)

                query = original_intent_data.get("query")
                action_context = None 
                location_confirmed_this_run = True
            else:
                response = {
                    "answer": "Entendido. Por favor, diga-me a sua nova localização (cidade e estado/país).",
                    "context": [],
                    "action_type": "REQUER_LOCALIZACAO",
                    "action_data": {"type": "AGUARDANDO_LOCALIZACAO", "original_intent_data": original_intent_data}
                }
                if redis_client:
                    redis_client.set(session_key, json.dumps(response.get("action_data")))
                    redis_client.expire(session_key, 900)
                return response
        
        elif context_type == "AGUARDANDO_CONFIRMACAO_CANCELAMENTO":
            cod_agendamento = action_context.get("codagendamento")
            
            if not cod_agendamento:
                response = {"answer": "Ocorreu um erro, não sei qual agendamento cancelar.", "context": []}
            elif "sim" in query.lower() or "confirmo" in query.lower():
                agendamento = agendamento_repo.get_by_id(db, codAgendamento=cod_agendamento)
                if not agendamento:
                     response = {"answer": "Erro: Agendamento não encontrado para cancelar.", "context": []}
                elif _perform_cancellation(db, paciente, agendamento):
                    response = {"answer": "Agendamento cancelado com sucesso. Posso ajudar em algo mais?", "context": []}
                else:
                    response = {"answer": "Ocorreu um erro ao tentar cancelar. Por favor, tente novamente.", "context": []}
            else:
                response = {"answer": "Entendido. O seu agendamento NÃO foi cancelado. Posso ajudar em algo mais?", "context": []}
            
            # Conversa terminada, limpa a memória e retorna
            if redis_client:
                redis_client.delete(session_key)
            return response

        elif context_type == "AGUARDANDO_CONFIRMACAO_REAGENDAMENTO":
            cod_agendamento = action_context.get("codagendamento")

            if not cod_agendamento:
                response = {"answer": "Ocorreu um erro, não sei qual agendamento reagendar.", "context": []}
            elif "sim" in query.lower() or "confirmo" in query.lower():
                agendamento = agendamento_repo.get_by_id(db, codAgendamento=cod_agendamento)
                if agendamento:
                    _perform_cancellation(db, paciente, agendamento)
                    response = {"answer": "Agendamento anterior cancelado. Agora, por favor, me diga o novo dia, horário e profissional para o reagendamento.", "context": []}
                else:
                    response = {"answer": "Erro: Agendamento não encontrado para reagendar.", "context": []}
            else:
                 response = {"answer": "Entendido. O seu agendamento foi mantido. Posso ajudar em algo mais?", "context": []}
            
            # Conversa terminada, limpa a memória e retorna
            if redis_client:
                redis_client.delete(session_key)
            return response
        elif context_type == "AGUARDANDO_CONFIRMACAO_SUGESTAO":
            sugestao = action_context.get("sugestao", {})
            
            if "sim" in query.lower() or "confirmo" in query.lower():
                # Chamar _handle_create_appointment com as entidades da sugestão
                print(f"DEBUG: Utilizador aceitou sugestão. Agendando com: {sugestao}")
                if redis_client:
                    redis_client.delete(session_key)
                
                original_query = original_intent_data.get("query", "")
                
                response = _handle_create_appointment(sugestao, telegram_id, db, query=original_query, intent="criar_agendamento")
            
            else:
                response = {
                    "answer": "Entendido. Por favor, me diga qual data e hora você gostaria de verificar.",
                    "context": [],
                    "action_type": None,
                    "action_data": None 
                }
                if redis_client:
                    redis_client.delete(session_key)
                    
            return response
        elif context_type == "REQUER_AUTORIZACAO_GCAL":
            query = original_intent_data.get("query")
            action_context = None 
            location_confirmed_this_run = True
    
    # ETAPA 2: Processar a pergunta atual (Se não houver 'action_context')
    intent_data = _get_intent_and_entities(query)
    intent = intent_data.get("intent")
    entities = intent_data.get("entities", {})

    # ETAPA 3: Verificar pré-requisitos para intenções de agendamento
    if intent in ['criar_agendamento', 'consulta_horarios']: 
        if not paciente.fuso_horario:
            # Se não tem fuso, é solicitado sua localização.
            response = {
                "answer": "Para garantir que o horário fique correto para si, por favor, pode me dizer em qual cidade e estado (ou país) você está?",
                "context": [],
                "action_type": "REQUER_LOCALIZACAO",
                "action_data": {"type": "AGUARDANDO_LOCALIZACAO", "original_intent_data": {"query": query, "intent": intent, "entities": entities}}
            }
            if redis_client:
                redis_client.set(session_key, json.dumps(response.get("action_data")))
                redis_client.expire(session_key, 900)
            return response

        ja_confirmou_hoje = _verificar_se_confirmou_hoje(telegram_id)

        if entities.get("nome_profissional"):
            hora_pref = _get_paciente_horario_preferido(db, paciente.codpaciente, paciente.fuso_horario)
    
            if hora_pref:
                if not location_confirmed_this_run and not ja_confirmou_hoje:
                    text = f"Para garantir que o horário sugerido fique correto, confirme se você ainda está em (Cidade: {paciente.cidade}, Estado: {paciente.estado})?"
                    response = {
                        "answer": text,
                        "context": [],
                        "action_type": "AGUARDANDO_CONFIRMACAO_LOCALIZACAO",
                        "action_data": {"type": "AGUARDANDO_CONFIRMACAO_LOCALIZACAO", "original_intent_data": {"query": query, "intent": intent, "entities": entities}}
                    }
                    if redis_client:
                        redis_client.set(session_key, json.dumps(response.get("action_data")))
                        redis_client.expire(session_key, 900)
                    return response
                # Encontrar a próxima data disponível para o profissional no horário preferido
                proxima_data = _encontrar_proxima_data_disponivel(db, entities.get("nome_profissional"), hora_pref)
                
                if proxima_data:
                    proxima_data_str = proxima_data.strftime('%Y-%m-%d')
                    proxima_data_fmt = proxima_data.strftime('%d/%m/%Y')

                    hora_pref_dt = datetime.combine(proxima_data, hora_pref)
                    hora_pref_dt = hora_pref_dt.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
                    hora_pref_local = hora_pref_dt.astimezone(ZoneInfo(paciente.fuso_horario))

                    hora_pref_str = hora_pref_local.strftime('%H:%M')
                    
                    # Criar resposta
                    response = {
                        "answer": f"Notei que costuma marcar consultas por volta das {hora_pref_str}.\n\nEncontrei um horário disponível na próxima data, dia {proxima_data_fmt} às {hora_pref_str}. Deseja agendar?",
                        "context": [],
                        "action_type": "REQUER_CONFIRMACAO_SUGESTAO",
                        "action_data": {
                            "type": "AGUARDANDO_CONFIRMACAO_SUGESTAO",
                            "original_intent_data": {"query": query, "intent": intent, "entities": entities},
                            "sugestao": {
                                "nome_profissional": entities.get("nome_profissional"),
                                "data": proxima_data_str,
                                "hora": hora_pref_str,
                                "tipo_consulta": entities.get("tipo_consulta", "Primeira Consulta")
                            }
                        }
                    }
                    
                    if redis_client:
                        redis_client.set(session_key, json.dumps(response.get("action_data")))
                        redis_client.expire(session_key, 900)
                    
                    return response
        elif not location_confirmed_this_run and not ja_confirmou_hoje:
            text = f"Para garantir que o horário fique correto para si, por favor, confirme a cidade e estado que (Cidade: {paciente.cidade}, Estado: {paciente.estado}) você está?"
            response = {
                "answer": text,
                "context": [],
                "action_type": "AGUARDANDO_CONFIRMACAO_LOCALIZACAO",
                "action_data": {"type": "AGUARDANDO_CONFIRMACAO_LOCALIZACAO", "original_intent_data": {"query": query, "intent": intent, "entities": entities}}
            }
            if redis_client:
                redis_client.set(session_key, json.dumps(response.get("action_data")))
                redis_client.expire(session_key, 900)
            return response

    # ETAPA 4: Roteamento Final para a Ação
    if intent == "criar_agendamento":
        response = _handle_create_appointment(entities, telegram_id, db, query, intent)
    elif intent == "consulta_horarios":
        response = _handle_schedule_query(entities, db)
    elif intent == "confirmar_agendamento":
        response = _handle_confirmation(telegram_id, db)
    elif intent == "saudacao":
        response = _handle_greeting(query)
    elif intent == "resposta_localizacao":
        response = _handle_localization_response(query, db, paciente, entities)
    elif intent == "cancelar_agendamento":
        response = _handle_cancel_request(telegram_id, db)
    elif intent == "modificar_agendamento":
        response = _handle_reschedule_request(telegram_id, db)
    else: # informacao_geral
        response = _handle_rag_query(query)

    # ETAPA 5: Guardar o Novo Estado ou Limpar o Antigo
    try:
        if redis_client:
            new_action_data = response.get("action_data")
            if new_action_data:
                redis_client.set(session_key, json.dumps(new_action_data))
                redis_client.expire(session_key, 900)
            else:
                redis_client.delete(session_key)
    except Exception as e:
        print(f"Erro ao GRAVAR contexto no Redis: {e}")

    return response

async def send_message(telegram_id: int, text: str):
    if not settings.TELEGRAM_TOKEN:
        print("ERRO: TELEGRAM_TOKEN não está configurado.")
        return
    
    telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": telegram_id,
        "text": text
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(telegram_url, json=payload)
            if response.status_code != 200:
                print(f"Erro ao enviar mensagem para {telegram_id}: {response.text}")
            else:
                print(f"Mensagem enviada com sucesso para {telegram_id}")
    except Exception as e:
        print(f"Exceção ao enviar mensagem para {telegram_id}: {e}")

def _verificar_se_confirmou_hoje(telegram_id: int) -> bool:
    if not redis_client:
        return False
    key = f"loc_confirmed_24h:{telegram_id}"
    return redis_client.exists(key)

def _registrar_confirmacao_hoje(telegram_id: int):
    if redis_client:
        key = f"loc_confirmed_24h:{telegram_id}"
        redis_client.set(key, "1", ex=86400)