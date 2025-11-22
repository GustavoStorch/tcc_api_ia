from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.services import ChatService
from app.dto.ChatDTO import ChatQueryRequest, ChatQueryResponse
from app.models.base import get_db
from app.api.deps import get_current_user
from app.models import UsuarioModel
from app.repository.PacienteRepository import paciente_repo 

router = APIRouter()

# Define rota que cria o chat/comunicação do assistente.
@router.post("/query", response_model=ChatQueryResponse)
def handle_chat_query(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: UsuarioModel.Usuario = Depends(get_current_user)
):
    try:
        try:
            telegram_id = int(request.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Session ID inválido para Telegram.")

        paciente = paciente_repo.get_by_telegram_id(db, telegram_id=telegram_id)
        if not paciente:
            try:
                paciente = paciente_repo.create_pacient(db=db, telegram_id=telegram_id, nome=request.nome_paciente)
            except Exception as e:
                 raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                    detail=f"Erro ao criar cadastro automático do paciente: {str(e)}"
                )

        # Chama a função principal do serviço, passando a mensagem e a sessão do DB
        result = ChatService.process_chat_query(request.query, request.session_id, request.nome_paciente, db, action_context=request.action_context)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro ao processar a sua pergunta: {e}"
        )