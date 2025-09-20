from google.oauth2 import service_account
from googleapiclient.discovery import build
from ..core.config import settings

SCOPES = ['https://www.googleapis.com/auth/calendar']

def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = None, attendees: list = None):
    """
    Cria um novo evento na agenda do Google.
    """
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