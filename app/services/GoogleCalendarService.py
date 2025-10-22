from google.oauth2 import service_account
from googleapiclient.discovery import build
from ..core.config import settings
from google.oauth2 import service_account, credentials
from typing import List, Optional

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
        creds = credentials.Credentials.from_authorized_user_info(
            info={
                "refresh_token": refresh_token,
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
        service.events().insert(
            calendarId='primary', 
            body=event_body
        ).execute()

        print("Evento inserido com sucesso no calendário pessoal do paciente.")
    except Exception as e:
        print(f"Ocorreu um erro ao criar o evento no calendário do paciente: {e}")