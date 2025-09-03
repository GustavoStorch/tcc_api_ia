from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.models.base import get_db
from app.api.deps import get_current_user
from app.models import UsuarioModel
from app.dto import AgendamentoDTO as agendamento_schema

router = APIRouter()

# Mantenha apenas a função de criar agendamento.
@router.post("/", response_model=agendamento_schema.AgendamentoRead, status_code=status.HTTP_201_CREATED)
def criar_agendamento(
    agendamento_data: agendamento_schema.AgendamentoCreate,
    db: Session = Depends(get_db),
    current_user: UsuarioModel.Usuario = Depends(get_current_user)
):
    """
    Cria um novo agendamento no sistema.
    """
    # (A lógica de criação de agendamento será implementada aqui)
    print(f"Novo agendamento criado para o paciente {agendamento_data.paciente_id} com o profissional {agendamento_data.profissional_id}")
    
    # Exemplo de retorno estático (deve ser substituído pela lógica real)
    return {
        "id": 101,
        "paciente_id": agendamento_data.paciente_id,
        "profissional_id": agendamento_data.profissional_id,
        "horario_inicio": agendamento_data.horario_inicio,
        "horario_fim": agendamento_data.horario_inicio,
        "valor_cobrado": 350.00,
        "situacao": "Agendado"
    }