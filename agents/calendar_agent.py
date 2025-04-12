import os
import logging
import pickle
from datetime import datetime, timezone
from typing import Dict, List, Optional

from dateutil import parser
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.adk.agents.llm_agent import LlmAgent

# Cargar variables de entorno
load_dotenv()

# Configuración de OAuth2 y Google Calendar
CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
CLIENT_SECRETS_PATH = os.getenv('GOOGLE_CLIENT_SECRETS_PATH', 'client_secrets.json')
MODEL_NAME = os.getenv('MODEL_NAME')
SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_google() -> Optional[Credentials]:
    """Autentica al usuario con la API de Google Calendar usando OAuth 2.0."""
    creds = None
    if os.path.exists(CREDENTIALS_PATH):
        try:
            with open(CREDENTIALS_PATH, 'rb') as token_file:
                creds = pickle.load(token_file)
        except Exception as e:
            logging.warning(f"No se pudieron cargar las credenciales desde {CREDENTIALS_PATH}: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logging.info("Refrescando token de acceso...")
                creds.refresh(Request())
                logging.info("Token refrescado exitosamente.")
            except Exception as e:
                logging.error(f"Error al refrescar token: {e}. Se requiere nueva autenticación.")
                if os.path.exists(CREDENTIALS_PATH):
                    try:
                        os.remove(CREDENTIALS_PATH)
                    except OSError as remove_err:
                        logging.error(f"No se pudo eliminar {CREDENTIALS_PATH}: {remove_err}")
                creds = None
        else:
            if not os.path.exists(CLIENT_SECRETS_PATH):
                logging.error(f"Falta el archivo '{CLIENT_SECRETS_PATH}'. Descárgalo desde Google Cloud Console.")
                return None
            try:
                logging.info("Iniciando flujo de autenticación OAuth 2.0...")
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logging.error(f"Error durante el flujo de autenticación: {e}")
                return None

        if creds:
            try:
                with open(CREDENTIALS_PATH, 'wb') as token_file:
                    pickle.dump(creds, token_file)
                logging.info(f"Credenciales nuevas guardadas en {CREDENTIALS_PATH}")
            except Exception as e:
                logging.error(f"Error al guardar credenciales: {e}")

    if creds and creds.valid:
        return creds
    else:
        logging.warning("No se pudieron obtener credenciales válidas.")
        return None

def _parse_datetime_str(datetime_str: str, default_tz=timezone.utc) -> Optional[str]:
    """Parsea una cadena de fecha/hora a formato ISO, añadiendo UTC si no tiene zona horaria."""
    if not datetime_str:
        return None
    try:
        dt = parser.parse(datetime_str)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            dt = dt.replace(tzinfo=default_tz)
        return dt.isoformat()
    except (ValueError, OverflowError) as e:
        logging.warning(f"Error al parsear '{datetime_str}': {e}")
        return None

def get_current_datetime() -> Dict[str, str]:
    """Obtiene la fecha y hora actual en formato ISO 8601 con zona horaria."""
    now = datetime.now().astimezone()
    now_iso = now.isoformat()
    logging.debug(f"get_current_datetime: {now_iso}")
    return {"status": "success", "current_datetime_iso": now_iso}

def create_calendar_event(summary: str, start_time: str, end_time: str,
                          description: str = "", location: str = "",
                          attendees: List[str] = []) -> Dict:
    creds = authenticate_google()
    if not creds:
        return {"status": "error", "message": "Autenticación requerida."}
    parsed_start = _parse_datetime_str(start_time)
    parsed_end = _parse_datetime_str(end_time)
    if not parsed_start or not parsed_end:
        return {"status": "error", "message": "Formato de fecha/hora inválido. Usar formato ISO 8601."}
    try:
        service = build('calendar', 'v3', credentials=creds)
        event_body = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {'dateTime': parsed_start},
            'end': {'dateTime': parsed_end},
            'attendees': [{'email': email} for email in attendees]
        }
        logging.debug(f"Creando evento: '{summary}'")
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        event_id = created_event.get('id')
        logging.debug(f"Evento creado con ID: {event_id}")
        return {'status': 'success', 'event_id': event_id, 'htmlLink': created_event.get('htmlLink')}
    except HttpError as error:
        logging.error(f"Error en API Google (crear evento): {error.resp.status} {error.reason}")
        return {"status": "error", "message": f"Error API: {error.resp.status} {error.reason}"}
    except Exception as e:
        logging.error(f"Error inesperado al crear evento: {e}", exc_info=True)
        return {"status": "error", "message": "Error inesperado del servidor."}

def list_calendar_events(time_min: str, time_max: str, max_results: int = 10) -> Dict:
    creds = authenticate_google()
    if not creds:
        return {"status": "error", "message": "Autenticación requerida."}

    parsed_time_min = _parse_datetime_str(time_min)
    parsed_time_max = _parse_datetime_str(time_max)
    safe_max_results = max(1, max_results) if isinstance(max_results, int) else 10

    if not parsed_time_min or not parsed_time_max:
        return {"status": "error", "message": "Formato de fecha/hora inválido para rango. Usar ISO 8601."}

    try:
        service = build('calendar', 'v3', credentials=creds)
        logging.debug(f"Listando eventos desde {parsed_time_min} hasta {parsed_time_max}")
        events_result = service.events().list(
            calendarId='primary',
            timeMin=parsed_time_min,
            timeMax=parsed_time_max,
            maxResults=safe_max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        logging.debug(f"Encontrados {len(events)} eventos.")
        return {
            'status': 'success',
            'events': [
                {
                    'summary': event.get('summary', ''),
                    'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                    'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
                    'description': event.get('description', ''),
                    'location': event.get('location', '')
                } for event in events
            ]
        }
    except HttpError as error:
        logging.error(f"Error en API Google (listar eventos): {error.resp.status} {error.reason}")
        return {"status": "error", "message": f"Error API: {error.resp.status} {error.reason}"}
    except Exception as e:
        logging.error(f"Error inesperado al listar eventos: {e}", exc_info=True)
        return {"status": "error", "message": "Error inesperado del servidor."}

# Creación del agente de calendario
calendar_assistant = LlmAgent(
    model=MODEL_NAME,
    name='calendar_assistant',
    instruction="""Eres un asistente especializado **únicamente** en gestionar eventos en Google Calendar.
Tienes acceso a estas herramientas: `get_current_datetime`, `create_calendar_event`, `list_calendar_events`.

**TU ÚNICA FUNCIÓN es crear y listar eventos de calendario según las peticiones del usuario.**

**FLUJO PARA FECHAS RELATIVAS:**
1. Si se utiliza una fecha relativa, PRIMERO llama a `get_current_datetime`.
2. Luego, usa la respuesta para calcular los argumentos ISO 8601 antes de llamar a las herramientas.

**REGLAS:**
- `create_calendar_event` y `list_calendar_events` requieren todos sus argumentos.
- Para `create_calendar_event`: usa una duración por defecto de 1 hora si no se especifica.
- Para `list_calendar_events`: usa `max_results=10` si no se especifica.
""",
    tools=[get_current_datetime, create_calendar_event, list_calendar_events],
)

# Exponer el agente de calendario para integración con el sistema multi-agente
root_agent = calendar_assistant
