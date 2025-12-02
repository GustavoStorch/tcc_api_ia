import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from app.main import app
from app.api.deps import get_current_user
from app.models import UsuarioModel

def mock_get_current_user():
    return UsuarioModel.Usuario(
        id=1, 
        usuario="admin_teste", 
        funcao=UsuarioModel.TipoFuncaoUsuario.Admin, 
        situacao=UsuarioModel.TipoSituacaoUsuario.Ativo
    )

app.dependency_overrides[get_current_user] = mock_get_current_user

def get_mock_lembretes():
    return [
        {
            "nome_paciente": "Paciente Lembrete",
            "telegram_chat_id": 123456789,
            "nome_profissional": "Dr. Lembrete",
            "horario_inicio": datetime.now() + timedelta(days=1),
            "dias_restantes": 1
        }
    ]

def test_get_lembretes_pendentes_sucesso(client, db_session):
    mock_data = get_mock_lembretes()

    with patch("app.services.LembreteService.lembrete_service.get_lembretes_pendentes", return_value=mock_data):
        
        response = client.get("/agendamentos/lembretes-pendentes") 
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 1
        if "nome_paciente" in data[0]:
            assert data[0]["nome_paciente"] == "Paciente Lembrete"
        elif "nomepaciente" in data[0]:
            assert data[0]["nomepaciente"] == "Paciente Lembrete"

def test_get_lembretes_vazio(client, db_session):
    with patch("app.services.LembreteService.lembrete_service.get_lembretes_pendentes", return_value=[]):
        response = client.get("/agendamentos/lembretes-pendentes")
        
        assert response.status_code == 200
        assert response.json() == []