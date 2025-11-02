from google.oauth2 import service_account
from googleapiclient.discovery import build
from ..core.config import settings
from google.oauth2 import service_account, credentials
from typing import List, Optional
from googleapiclient.errors import HttpError
from cryptography.fernet import Fernet 
from datetime import date, datetime, timedelta, time
import pytz

SCOPES = ['https://www.googleapis.com/auth/calendar']
SCOPESPACIENTES = ['https://www.googleapis.com/auth/calendar.events']

def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = None, attendees: list = None):
    # Criação de um novo evento dentro do Google Calendar.
    try:
        creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Sao_Paulo', 
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Sao_Paulo',
            },
        }
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        created_event = service.events().insert(
            calendarId=settings.GOOGLE_CALENDAR_ID, 
            body=event
        ).execute()
        
        print(f"Evento criado com sucesso: {created_event.get('htmlLink')}")
        return created_event.get('id')

    except Exception as e:
        print(f"Ocorreu um erro ao criar o evento no Google Calendar: {e}")
        raise

def create_patient_calendar_event(refresh_token: str, summary: str, start_time: str, end_time: str, timeZone: str, description: Optional[str] = None):
    try:
        f = Fernet(settings.FERNET_KEY.encode('utf-8'))
        if refresh_token.startswith('\\x'):
            cleaned_hex_string = refresh_token[2:]
        else:
            cleaned_hex_string = refresh_token
        base64_token_bytes = bytes.fromhex(cleaned_hex_string)
        decrypted_token = f.decrypt(base64_token_bytes).decode('utf-8')

        creds = credentials.Credentials.from_authorized_user_info(
            info={
                "refresh_token": decrypted_token,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
            },
            scopes=SCOPESPACIENTES
        )
        
        service = build('calendar', 'v3', credentials=creds)
        
        event_body = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': timeZone},
            'end': {'dateTime': end_time, 'timeZone': timeZone},
        }

        # Usa 'primary' para gravar ao calendário principal do utilizador autenticado
        created_event = service.events().insert(
            calendarId='primary', 
            body=event_body
        ).execute()

        print("Evento inserido com sucesso no calendário pessoal do paciente.")

        return created_event.get('id')
    except Exception as e:
        print(f"Ocorreu um erro ao criar o evento no calendário do paciente: {e}")

def delete_calendar_event(event_id: str):
    try:
        creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        service = build('calendar', 'v3', credentials=creds)
        
        service.events().delete(
            calendarId=settings.GOOGLE_CALENDAR_ID, 
            eventId=event_id
        ).execute()
        
        print(f"Evento da Clínica (ID: {event_id}) deletado com sucesso.")

    except HttpError as e:
        if e.resp.status == 404:
            print(f"AVISO: Evento da Clínica (ID: {event_id}) não encontrado para deleção (já foi deletado?).")
        else:
            print(f"Ocorreu um erro ao deletar o evento da Clínica: {e}")
            raise
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao deletar evento da Clínica: {e}")
        raise

def delete_patient_calendar_event(refresh_token: str, event_id: str):
    try:
        creds = credentials.Credentials.from_authorized_user_info(
            info={
                "refresh_token": refresh_token,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
            },
            scopes=SCOPESPACIENTES
        )
        
        service = build('calendar', 'v3', credentials=creds)
        
        service.events().delete(
            calendarId='primary', 
            eventId=event_id
        ).execute()
        
        print(f"Evento do Paciente (ID: {event_id}) deletado com sucesso.")

    except HttpError as e:
        if e.resp.status == 404:
            print(f"AVISO: Evento do Paciente (ID: {event_id}) não encontrado para deleção (já foi deletado?).")
        elif e.resp.status == 401 or e.resp.status == 400:
             print(f"AVISO: Falha ao deletar evento do Paciente (ID: {event_id}). Token pode ter sido revogado.")
        else:
            print(f"Ocorreu um erro Http ao deletar o evento do Paciente: {e}")
            raise
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao deletar evento do Paciente: {e}")
        raise

def esta_ocupado_google_calendar(nome_profissional: str, data: date, hora: time) -> bool:
    try:
        slot_inicio = datetime.combine(data, hora)
        slot_fim = slot_inicio + timedelta(minutes=60)  

        fuso = pytz.timezone('America/Sao_Paulo')
        slot_inicio_aware = fuso.localize(slot_inicio)
        slot_fim_aware = fuso.localize(slot_fim)

        timeMin = slot_inicio_aware.isoformat()
        timeMax = slot_fim_aware.isoformat()

        creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=creds)

        events_result = service.events().list(
            calendarId=settings.GOOGLE_CALENDAR_ID, 
            timeMin=timeMin,
            timeMax=timeMax,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        eventos_relevantes = [e for e in events if nome_profissional.lower() in e.get('summary', '').lower()]

        return len(eventos_relevantes) > 0

    except Exception as e:
        print(f"Erro ao consultar Google Calendar: {e}")
        return False  
