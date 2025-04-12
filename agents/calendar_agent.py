# agents/calendar_agent.py
import os
import logging
import pickle
from typing import Dict, List, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.adk.agents.llm_agent import LlmAgent

from agents import utils
import config
from constants import CALENDAR_PROMPT

def authenticate_google() -> Optional[Credentials]:
    """Autentica al usuario usando OAuth 2.0 con Google Calendar."""
    creds = None
    if os.path.exists(config.GOOGLE_CREDENTIALS_PATH):
        try:
            with open(config.GOOGLE_CREDENTIALS_PATH, 'rb') as token_file:
                creds = pickle.load(token_file)
        except Exception as e:
            logging.warning(f"No se pudieron cargar credenciales desde {config.GOOGLE_CREDENTIALS_PATH}: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logging.info("Refrescando token de acceso...")
                creds.refresh(Request())
                logging.info("Token refrescado exitosamente.")
            except Exception as e:
                logging.error(f"Error al refrescar token: {e}. Se requiere nueva autenticación.")
                if os.path.exists(config.GOOGLE_CREDENTIALS_PATH):
                    try:
                        os.remove(config.GOOGLE_CREDENTIALS_PATH)
                    except OSError as remove_err:
                        logging.error(f"No se pudo eliminar {config.GOOGLE_CREDENTIALS_PATH}: {remove_err}")
                creds = None
        else:
            if not os.path.exists(config.GOOGLE_CLIENT_SECRETS_PATH):
                logging.error(f"Falta el archivo '{config.GOOGLE_CLIENT_SECRETS_PATH}'. Descárgalo desde Google Cloud Console.")
                return None
            try:
                logging.info("Iniciando flujo de autenticación OAuth 2.0...")
                flow = InstalledAppFlow.from_client_secrets_file(config.GOOGLE_CLIENT_SECRETS_PATH, config.SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logging.error(f"Error durante el flujo de autenticación: {e}")
                return None

        if creds:
            try:
                with open(config.GOOGLE_CREDENTIALS_PATH, 'wb') as token_file:
                    pickle.dump(creds, token_file)
                logging.info(f"Credenciales nuevas guardadas en {config.GOOGLE_CREDENTIALS_PATH}")
            except Exception as e:
                logging.error(f"Error al guardar credenciales: {e}")

    if creds and creds.valid:
        return creds
    else:
        logging.warning("No se pudieron obtener credenciales válidas.")
        return None

def create_calendar_event(summary: str, start_time: str, end_time: str,
                          description: str = "", location: str = "",
                          attendees: List[str] = []) -> Dict:
    creds = authenticate_google()
    if not creds:
        return {"status": "error", "message": "Autenticación requerida."}
    parsed_start = utils.parse_datetime_str(start_time)
    parsed_end = utils.parse_datetime_str(end_time)
    if not parsed_start or not parsed_end:
        return {"status": "error", "message": "Formato de fecha/hora inválido. Usar ISO 8601."}
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
    parsed_time_min = utils.parse_datetime_str(time_min)
    parsed_time_max = utils.parse_datetime_str(time_max)
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
        return {'status': 'success', 'events': [
            {
                'summary': event.get('summary', ''),
                'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
                'description': event.get('description', ''),
                'location': event.get('location', '')
            } for event in events
        ]}
    except HttpError as error:
        logging.error(f"Error en API Google (listar eventos): {error.resp.status} {error.reason}")
        return {"status": "error", "message": f"Error API: {error.resp.status} {error.reason}"}
    except Exception as e:
        logging.error(f"Error inesperado al listar eventos: {e}", exc_info=True)
        return {"status": "error", "message": "Error inesperado del servidor."}

# Creación del agente de calendario usando LlmAgent
calendar_assistant = LlmAgent(
    model=config.MODEL_NAME,
    name='calendar_assistant',
    instruction=CALENDAR_PROMPT,
    tools=[utils.get_current_datetime, create_calendar_event, list_calendar_events],
)

root_agent = calendar_assistant
