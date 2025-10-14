from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.models.base import get_db
from app.services.LembreteService import lembrete_service
from app.dto.LembreteDTO import LembretePendenteResponse
from app.api.deps import get_current_user
from app.models import UsuarioModel

router = APIRouter()

@router.get("/lembretes-pendentes", response_model=List[LembretePendenteResponse])
def get_lembretes(
    db: Session = Depends(get_db),
    current_user: UsuarioModel.Usuario = Depends(get_current_user)
):
    lembretes = lembrete_service.get_lembretes_pendentes(db)
    return lembretes