from sqlalchemy.orm import Session
from sqlalchemy import func
import google.generativeai as genai
from pinecone import Pinecone
from datetime import date, datetime, timedelta
import json

from ..core.config import settings
from ..models import AgendamentoModel, GradeHorariosModel
from ..repository.ProfissionalRepository import profissional_repo
from ..repository.PacienteRepository import paciente_repo 
from ..repository.AgendamentoRepository import agendamento_repo
from ..services.SincronizacaoVetorialService import embedder
from ..models.PacienteModel import Paciente
from ..dto.AgendamentoDTO import AgendamentoCreate
from ..services.AgendamentoService import criar_novo_agendamento

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
    As intenções possíveis são: 'saudacao', 'confirmar_agendamento', 'criar_agendamento', 'consulta_horarios', 'informacao_geral', 'resposta_localizacao'.

    - 'saudacao' é para cumprimentos gerais como "Oi", "Bom dia", "Tudo bem?".
    - 'confirmar_agendamento' é usado para respostas como "Sim", "Confirmo", "Ok, confirmado".
    - 'criar_agendamento' é usado quando o utilizador pede explicitamente para marcar uma consulta.
    - 'consulta_horarios' é para quando o utilizador pergunta sobre horários livres.
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

    Pergunta do Utilizador: "{query}"
    """
    response = intent_model.generate_content(prompt)
    try:
        # Limpa a resposta para garantir que seja um JSON válido
        clean_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean_response)
    except (json.JSONDecodeError, AttributeError):
        return {"intent": "informacao_geral", "entities": {}}


# Busca os horários disponíveis com base na análise do Gemini
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
    
    grade_do_dia = db.query(GradeHorariosModel.GradeHorarios).filter(GradeHorariosModel.GradeHorarios.codprofissional == profissional.codprofissional, GradeHorariosModel.GradeHorarios.dia == dia_semana_str).first()
    if not grade_do_dia:
        return {"answer": f"O(A) {profissional.nome} não atende neste dia da semana.", "context": []}

    agendamentos_ocupados = db.query(AgendamentoModel.Agendamento.horario_inicio).filter(AgendamentoModel.Agendamento.codprofissional == profissional.codprofissional, func.date(AgendamentoModel.Agendamento.horario_inicio) == data).all()
    horarios_ocupados = {ag.horario_inicio.time() for ag in agendamentos_ocupados}
    
    todos_os_slots = set()
    duracao_consulta = timedelta(minutes=60)
    turnos = [(grade_do_dia.horainciomanha, grade_do_dia.horafimmanha), (grade_do_dia.horainciotarde, grade_do_dia.horafimtarde)]
    
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
def _handle_create_appointment(entities: dict, telegram_id: int, db: Session) -> dict:
    paciente = paciente_repo.get_by_telegram_id(db, telegram_id=telegram_id)
    if not paciente:
        return {"answer": "Não consegui encontrar o seu registo de paciente.", "context": []}

    if not paciente.token:
        auth_link = f"http://127.0.0.1:8000/auth/google/login?telegram_id={telegram_id}"
        return {
            "answer": "Para adicionar o agendamento ao seu Google Calendar, preciso da sua permissão. Por favor, clique no link abaixo para autorizar.",
            "context": [],
            "action_type": "REQUER_AUTORIZACAO_GCAL",
            "action_data": {"authorization_url": auth_link}
        }

    nome_profissional = entities.get("nome_profissional")
    data_str = entities.get("data")
    hora_str = entities.get("hora")
    tipo_consulta = entities.get("tipo_consulta", "Primeira Consulta")

    if not all([nome_profissional, data_str, hora_str]):
        return {"answer": "Faltam informações para o agendamento (profissional, data ou hora).", "context": []}

    try:
        agendamento_para_criar = AgendamentoCreate(
            nomepaciente=paciente.nome,
            nomeprofissional=nome_profissional,
            nometipoconsulta=tipo_consulta,
            codclinica=1,
            horario_inicio=datetime.fromisoformat(f"{data_str}T{hora_str}:00")
        )

        novo_agendamento = criar_novo_agendamento(db=db, agendamento_data=agendamento_para_criar)

        data_formatada = novo_agendamento.horario_inicio.strftime('%d/%m/%Y às %H:%M')
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
    
def _handle_greeting(query: str) -> dict:
    return {"answer": "Olá! Bem vindo à nossa clinica. Como posso ajudar?", "context": [], "action_type": None, "action_data": None}

# def process_chat_query(query: str, telegram_id: int, db: Session) -> dict:
#     if intent_model is None or pinecone_index is None:
#         raise ConnectionError("Serviços de IA não inicializados.")
    
#     # Identifica a intenção
#     intent_data = _get_intent_and_entities(query)
#     intent = intent_data.get("intent")
#     entities = intent_data.get("entities", {})

#     # Tomada de ação com base na intenção
#     if intent == "consulta_horarios":
#         print("DEBUG: Intenção 'consulta_horarios' detetada.")
#         return _handle_schedule_query(entities, db)
#     elif intent == "criar_agendamento":
#         print("DEBUG: Intenção 'criar_agendamento' detetada.")
#         return _handle_create_appointment(entities, telegram_id, db)
#     elif intent == "confirmar_agendamento":
#         print("DEBUG: Intenção 'confirmar_agendamento' detetada.")
#         return _handle_confirmation(telegram_id, db)
#     else:
#         print("DEBUG: Intenção 'informacao_geral' detetada.")
#         return _handle_rag_query(query)

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


def process_chat_query(query: str, session_id: str, db: Session, action_context: dict | None = None) -> dict:
    try:
        telegram_id = int(session_id)
    except (ValueError, TypeError):
        return {"answer": "ID de sessão inválido.", "context": [], "action_type": None, "action_data": None}

    paciente = paciente_repo.get_by_telegram_id(db, telegram_id=telegram_id)
    if not paciente:
        return {"answer": "Não consegui encontrar o seu registo de paciente.", "context": [], "action_type": None, "action_data": None}

    if action_context:
        context_type = action_context.get("type")
        original_intent_data = action_context.get("original_intent_data", {})

        if context_type == "AGUARDANDO_LOCALIZACAO":
            fuso_inferido = _inferir_fuso_horario_de_local(query)
            if fuso_inferido:
                paciente_repo.update_fuso_horario(db, paciente=paciente, fuso_horario=fuso_inferido)
                # Fuso horário guardado! Agora, vamos processar a pergunta original novamente.
                query = original_intent_data.get("query")
            else:
                return {"answer": "Peço desculpa, não consegui identificar um fuso horário para essa localização. Pode tentar novamente?", "context": [], "action_type": "REQUER_LOCALIZACAO", "action_data": action_context}

        elif context_type == "AGUARDANDO_CONFIRMACAO_LOCALIZACAO":
            if "sim" in query.lower() or "correto" in query.lower():
                query = original_intent_data.get("query")
            else:
                return {
                    "answer": "Entendido. Por favor, diga-me a sua nova localização (cidade e estado/país).",
                    "context": [],
                    "action_type": "REQUER_LOCALIZACAO",
                    "action_data": {"type": "AGUARDANDO_LOCALIZACAO", "original_intent_data": original_intent_data}
                }
    
    intent_data = _get_intent_and_entities(query)
    intent = intent_data.get("intent")
    entities = intent_data.get("entities", {})

    if intent in ['criar_agendamento']:
        if not paciente.fuso_horario:
            # Se não tem fuso, é solicitado sua localização.
            return {
                "answer": "Para garantir que o horário fique correto para si, por favor, pode me dizer em qual cidade e estado (ou país) você está?",
                "context": [],
                "action_type": "REQUER_LOCALIZACAO",
                "action_data": {"type": "AGUARDANDO_LOCALIZACAO", "original_intent_data": {"query": query, "intent": intent, "entities": entities}}
            }
        # else:
        #     text = f"Para garantir que o horário fique correto para si, por favor, confirme a cidade e estado que (Cidade: {paciente.cidade}, Estado: {paciente.estado}) você está?"
        #     return {
        #         "answer": text,
        #         "context": [],
        #         "action_type": "CONFIRMAR_LOCALIZACAO",
        #         "action_data": {"type": "AGUARDANDO_LOCALIZACAO", "original_intent_data": {"query": query, "intent": intent, "entities": entities}}
        #     }

    if intent == "criar_agendamento":
        return _handle_create_appointment(entities, telegram_id, db)
    elif intent == "consulta_horarios":
        return _handle_schedule_query(entities, db)
    elif intent == "confirmar_agendamento":
        return _handle_confirmation(telegram_id, db)
    elif intent == "saudacao":
        return _handle_greeting(query)
    elif intent == "resposta_localizacao":
        return _handle_localization_response(query, db, paciente, entities)
    else: # informacao_geral
        return _handle_rag_query(query)