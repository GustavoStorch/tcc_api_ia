from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.services import ChatService
from app.dto.ChatDTO import ChatQueryRequest, ChatQueryResponse
from app.models.base import get_db
from app.api.deps import get_current_user
from app.models import UsuarioModel

router = APIRouter()

@router.post("/query", response_model=ChatQueryResponse)
def handle_chat_query(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: UsuarioModel.Usuario = Depends(get_current_user)
):
    try:
        # Chama a função principal do serviço, passando a mensagem e a sessão do DB
        result = ChatService.process_chat_query(request.query, db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro ao processar a sua pergunta: {e}"
        )