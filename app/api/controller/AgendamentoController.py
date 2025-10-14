from fastapi import APIRouter, Depends, status, HTTPException, Form
from sqlalchemy.orm import Session

from app.models.base import get_db
from app.api.deps import get_current_user
from app.models import UsuarioModel
from app.dto import AgendamentoDTO as agendamento_schema
from app.services import AgendamentoService

router = APIRouter()

# Define rota que cria o agendamento
@router.post("/", response_model=agendamento_schema.AgendamentoRead, status_code=status.HTTP_201_CREATED)
def criar_agendamento(
    # agendamento_data: agendamento_schema.AgendamentoCreate,
    nomepaciente: str = Form(...),
    nomeprofissional: str = Form(...),
    nometipoconsulta: str = Form(...),
    codclinica: int = Form(...),
    horario_inicio: str = Form(...),
    db: Session = Depends(get_db),
    current_user: UsuarioModel.Usuario = Depends(get_current_user)
):
    try:
        agendamento_data = agendamento_schema.AgendamentoCreate(
            nomepaciente=nomepaciente,
            nomeprofissional=nomeprofissional,
            nometipoconsulta=nometipoconsulta,
            codclinica=codclinica,
            horario_inicio=horario_inicio
        )
        novo_agendamento = AgendamentoService.criar_novo_agendamento(db=db, agendamento_data=agendamento_data)
        return novo_agendamento
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocorreu um erro ao criar o agendamento.")