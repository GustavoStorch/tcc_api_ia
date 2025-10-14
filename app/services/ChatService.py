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
from ..services.SincronizacaoVetorialService import embedder

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
    # prompt = f"""
    # Analise a pergunta do utilizador e classifique a sua intenção.
    # As intenções possíveis são: 'consulta_horarios' ou 'informacao_geral'.

    # Se a intenção for 'consulta_horarios', extraia o nome do profissional e a data desejada no formato AAAA-MM-DD.
    # Considere que a data de hoje é {today}.
    # Exemplos de datas relativas: 'amanhã', 'depois de amanhã', 'próxima segunda-feira'.

    # A sua resposta DEVE ser apenas um objeto JSON válido.

    # Exemplo 1:
    # Pergunta: "Quais os horários da Dra. Ana para amanhã?"
    # Resposta: {{"intent": "consulta_horarios", "entities": {{"nome_profissional": "Dra. Ana", "data": "2025-09-01"}}}}

    # Exemplo 2:
    # Pergunta: "Qual o CRM do Dr. Carlos?"
    # Resposta: {{"intent": "informacao_geral", "entities": {{}}}}

    # Pergunta do Utilizador: "{query}"
    # """
    prompt = f"""
    Analise a pergunta do utilizador e classifique a sua intenção.
    As intenções possíveis são: 'criar_agendamento', 'consulta_horarios', ou 'informacao_geral'.

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

##### FUNCIONAL
# def _handle_create_appointment(entities: dict, db: Session) -> dict:
#     nome_profissional = entities.get("nome_profissional")
#     data_str = entities.get("data")
#     hora_str = entities.get("hora")
#     tipo_consulta = entities.get("tipo_consulta", "Primeira Consulta")

#     if not all([nome_profissional, data_str, hora_str]):
#         return {
#             "answer": "Para criar um agendamento, preciso do nome do profissional, da data e da hora.",
#             "context": [],
#             "action_type": None,
#             "action_data": None
#         }

#     try:
#         horario_inicio = datetime.fromisoformat(f"{data_str}T{hora_str}:00").isoformat()
#     except ValueError:
#         return {
#             "answer": f"A data '{data_str}' ou hora '{hora_str}' não parecem estar num formato válido.",
#             "context": [],
#             "action_type": None,
#             "action_data": None
#         }

#     dados_agendamento = {
#         "nomepaciente": "Gustavo Storch", 
#         "nomeprofissional": nome_profissional,
#         "nometipoconsulta": tipo_consulta,
#         "codclinica": 1, 
#         "horario_inicio": horario_inicio
#     }
    
#     resposta_para_utilizador = f"Entendido! A preparar o agendamento com {nome_profissional} para {data_str} às {hora_str}. Só um momento."

#     # Retorna a estrutura completa
#     return {
#         "answer": resposta_para_utilizador,
#         "context": [],
#         "action_type": "CRIAR_AGENDAMENTO",
#         "action_data": dados_agendamento
#     }

def _handle_create_appointment(entities: dict, telegram_id: int, db: Session) -> dict:
    # 1. Busca o paciente pelo telegram_id
    paciente = paciente_repo.get_by_telegram_id(db, telegram_id=telegram_id)
    if not paciente:
        return {
            "answer": "Não consegui encontrar o seu registo de paciente. Por favor, contacte a clínica.",
            "context": [], "action_type": None, "action_data": None
        }

    # 2. VERIFICA SE O PACIENTE JÁ DEU PERMISSÃO (se tem o token)
    if not paciente.token:
        # Se não tiver o token, a ação é pedir autorização.
        auth_link = f"http://127.0.0.1:8000/auth/google/login?telegram_id={telegram_id}"
        return {
            "answer": "Para adicionar o agendamento ao seu Google Calendar, preciso da sua permissão. Por favor, clique no link abaixo para autorizar.",
            "context": [],
            "action_type": "REQUER_AUTORIZACAO_GCAL",
            "action_data": {"authorization_url": auth_link}
        }

    # 3. Se já tem permissão, segue o fluxo normal
    nome_profissional = entities.get("nome_profissional")
    data_str = entities.get("data")
    hora_str = entities.get("hora")
    tipo_consulta = entities.get("tipo_consulta", "Primeira Consulta")

    if not all([nome_profissional, data_str, hora_str]):
        return { "answer": "Faltam informações para o agendamento (profissional, data ou hora).", "context": [] }

    try:
        horario_inicio = datetime.fromisoformat(f"{data_str}T{hora_str}:00").isoformat()
    except ValueError:
        return { "answer": f"A data '{data_str}' ou hora '{hora_str}' não são válidas.", "context": [] }

    dados_agendamento = {
        "nomepaciente": paciente.nome, 
        "nomeprofissional": nome_profissional,
        "nometipoconsulta": tipo_consulta,
        "codclinica": 1, 
        "horario_inicio": horario_inicio
    }
    
    return {
        "answer": f"A preparar o agendamento com {nome_profissional} para {data_str} às {hora_str}. Só um momento.",
        "context": [],
        "action_type": "CRIAR_AGENDAMENTO",
        "action_data": dados_agendamento
    }


def process_chat_query(query: str, telegram_id: int, db: Session) -> dict:
    if intent_model is None or pinecone_index is None:
        raise ConnectionError("Serviços de IA não inicializados.")

    # Identifica a intenção
    intent_data = _get_intent_and_entities(query)
    intent = intent_data.get("intent")
    entities = intent_data.get("entities", {})

    # Tomada de ação com base na intenção
    if intent == "consulta_horarios":
        print("DEBUG: Intenção 'consulta_horarios' detetada.")
        return _handle_schedule_query(entities, db)
    elif intent == "criar_agendamento":
        print("DEBUG: Intenção 'criar_agendamento' detetada.")
        return _handle_create_appointment(entities, telegram_id, db)
    else:
        print("DEBUG: Intenção 'informacao_geral' detetada.")
        return _handle_rag_query(query)