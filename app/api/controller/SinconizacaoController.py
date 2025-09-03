from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from app.models.base import get_db
from app.services import SincronizacaoVetorialService
from app.api.deps import get_current_user 
from app.models import UsuarioModel 

router = APIRouter()

@router.post("/vector-db", status_code=status.HTTP_202_ACCEPTED)
def trigger_sync(
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    current_user: UsuarioModel.Usuario = Depends(get_current_user) 
):
    # Inicia o processo de sincronização dos dados do Postgress para o bd vetorial. Permissão somente para Administradores
    if current_user.funcao != UsuarioModel.TipoFuncaoUsuario.Admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação."
        )

    # Deixa o processo rodando em segundo plano
    background_tasks.add_task(SincronizacaoVetorialService.sincronizar_base_conhecimento, db)
    return {"message": "Processo de sincronização da base de conhecimento iniciado em background."}