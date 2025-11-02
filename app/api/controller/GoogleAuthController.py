from fastapi import APIRouter, Depends, HTTPException, status, Query
from starlette.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx
from typing import Optional
from cryptography.fernet import Fernet 

from ...core.config import settings
from ...models.base import get_db
from ...repository.PacienteRepository import PacienteRepository
from ...services.ChatService import process_chat_query, send_message

router = APIRouter()

@router.get("/google/login")
def google_login(
    telegram_id: int = Query(...) 
):
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/calendar.events&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={telegram_id}"
    )
    return RedirectResponse(auth_url)

@router.get("/google/callback")
async def google_callback(
    code: str, 
    state: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parâmetro 'state' em falta. Não é possível identificar o utilizador."
        )
        
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Erro ao trocar o código: {response.text}")

    f = Fernet(settings.FERNET_KEY.encode('utf-8'))

    token_data = response.json()
    # refresh_token = token_data.get("refresh_token")
    refresh_token = f.encrypt(token_data.get("refresh_token").encode('utf-8'))

    if not refresh_token:
        return {"status": "info", "message": "Autorização já concedida anteriormente."}

    try:
        telegram_id = int(state)
        paciente_repo = PacienteRepository()
        paciente = paciente_repo.get_by_telegram_id(db, telegram_id=telegram_id)
        
        if not paciente:
            print(f"ERRO: Paciente com Telegram ID {telegram_id} não encontrado.")
            raise HTTPException(status_code=404, detail="Paciente não encontrado.")
            
        paciente_repo.update_refresh_token(db, paciente=paciente, token=refresh_token)
        print(f"Token de atualização para o paciente '{paciente.nome}' foi guardado com sucesso.")

        response_dict = process_chat_query(
            query="", 
            session_id=telegram_id,
            db=db
        )

        answer_to_user = response_dict.get("answer")

        if answer_to_user:
            # 4. Enviar a resposta de volta para o chat do utilizador
            await send_message(telegram_id, answer_to_user)
        else:
            # Fallback caso algo corra mal no processamento
            await send_message(telegram_id, "Autorização concluída! Pode voltar ao chat e tentar novamente.")
            print(f"AVISO: process_chat_query não retornou um 'answer' para {telegram_id}.")

    except Exception as e:
        if isinstance(e, (ValueError, TypeError)):
            raise HTTPException(status_code=400, detail="Parâmetro 'state' inválido.")
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno ao processar a autorização: {e}")
    
    return {"status": "sucesso", "message": "Autorização concedida! Pode fechar esta página."}