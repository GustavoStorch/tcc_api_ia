import pytest
from unittest.mock import patch, MagicMock
from app.main import app
from app.api.deps import get_current_user
from app.models import UsuarioModel, PacienteModel

def mock_get_current_user():
    return UsuarioModel.Usuario(
        id=1, 
        usuario="admin_teste", 
        funcao="Admin", 
        situacao="Ativo"
    )

app.dependency_overrides[get_current_user] = mock_get_current_user

@pytest.fixture
def mock_chat_services():
    with patch("app.services.ChatService.intent_model") as mock_intent, \
         patch("app.services.ChatService.genai.GenerativeModel") as mock_genai_cls, \
         patch("app.services.ChatService.pinecone_index") as mock_pinecone, \
         patch("app.services.ChatService.redis_client") as mock_redis, \
         patch("app.services.ChatService.embedder") as mock_embedder:
        
        redis_store = {}
        mock_redis.get.side_effect = lambda k: redis_store.get(k)
        mock_redis.set.side_effect = lambda k, v, ex=None: redis_store.update({k: v})
        mock_redis.delete.side_effect = lambda k: redis_store.pop(k, None)
        
        mock_embedder.encode.return_value = [[0.1, 0.2, 0.3]]

        yield {
            "intent_model": mock_intent,
            "genai_cls": mock_genai_cls,
            "pinecone": mock_pinecone
        }

def test_chat_fluxo_novo_paciente_saudacao(client, db_session, mock_chat_services):
    session_id_novo = "999999"
    nome_paciente = "Visitante Teste"
    
    mock_response_intent = MagicMock()
    mock_response_intent.text = '{"intent": "saudacao", "entities": {}}'
    mock_chat_services["intent_model"].generate_content.return_value = mock_response_intent

    response = client.post(
        "/chat/query", 
        json={
            "query": "Olá, bom dia!",
            "session_id": session_id_novo,
            "nome_paciente": nome_paciente
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "Olá" in data["answer"] or "Bem vindo" in data["answer"]

    paciente_db = db_session.query(PacienteModel.Paciente).filter_by(telegram_chat_id=int(session_id_novo)).first()
    assert paciente_db is not None
    assert paciente_db.nome == nome_paciente
    assert paciente_db.situacao == "Ativo"

def test_chat_exige_localizacao_sem_fuso(client, db_session, mock_chat_services):
    session_id = "888888"
    paciente = PacienteModel.Paciente(
        telegram_chat_id=int(session_id),
        nome="Paciente Sem Fuso",
        cpf=f"TEMP_{session_id}",
        telefone="00000000",
        fuso_horario=None, 
        situacao="Ativo"
    )
    db_session.add(paciente)
    db_session.commit()

    mock_response_intent = MagicMock()
    mock_response_intent.text = '{"intent": "criar_agendamento", "entities": {"nome_profissional": "Dr. Teste"}}'
    mock_chat_services["intent_model"].generate_content.return_value = mock_response_intent

    response = client.post(
        "/chat/query", 
        json={
            "query": "Quero marcar consulta",
            "session_id": session_id,
            "nome_paciente": "Paciente Sem Fuso"
        }
    )

    assert response.status_code == 200
    data = response.json()
    
    assert data["action_type"] == "REQUER_LOCALIZACAO"
    assert "cidade e estado" in data["answer"]

def test_chat_session_id_invalido(client):
    response = client.post(
        "/chat/query",
        json={
            "query": "Oi",
            "session_id": "texto_invalido",
            "nome_paciente": "Teste"
        }
    )
    
    assert response.status_code == 400
    assert "Session ID inválido" in response.json()["detail"]