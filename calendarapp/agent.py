from google.adk.agents.llm_agent import LlmAgent
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Dict, List, Optional
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil import parser

# Cargar variables de entorno
load_dotenv()

# Configuración de OAuth2
CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
CLIENT_SECRETS_PATH = os.getenv('GOOGLE_CLIENT_SECRETS_PATH', 'client_secrets.json')
MODEL_NAME = os.getenv('MODEL_NAME')
SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_google() -> Optional[Credentials]:
    """Autentica al usuario con Google Calendar API usando OAuth 2.0."""
    creds = None
    if os.path.exists(CREDENTIALS_PATH):
        try:
            with open(CREDENTIALS_PATH, 'rb') as token_file:
                creds = pickle.load(token_file)
        except Exception as e:
             logging.warning(f"No se pudieron cargar credenciales desde {CREDENTIALS_PATH} ({e}). Se intentará nueva autenticación.")
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
                  logging.error(f"Falta el archivo '{CLIENT_SECRETS_PATH}'. "
                                "Descárgalo desde Google Cloud Console.")
                  return None
             try:
                 logging.info("Iniciando flujo de autenticación OAuth 2.0 (requiere interacción del usuario)...") 
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
                  logging.error(f"Error al guardar credenciales en {CREDENTIALS_PATH}: {e}")

    if creds and creds.valid:
        return creds
    else:
        logging.warning("No se pudieron obtener credenciales válidas.")
        return None

def _parse_datetime_str(datetime_str: str, default_tz=timezone.utc) -> Optional[str]:
    """Intenta parsear una cadena de fecha/hora a formato ISO, añadiendo UTC si no tiene timezone."""
    if not datetime_str: return None
    try:
        dt = parser.parse(datetime_str)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            dt = dt.replace(tzinfo=default_tz) 
        return dt.isoformat()
    except (ValueError, OverflowError) as e:
        logging.warning(f"No se pudo parsear la fecha/hora '{datetime_str}': {e}")
        return None

def get_current_datetime() -> Dict[str, str]:
    """Obtiene la fecha y hora actual del sistema en formato ISO 8601 con timezone."""
    now = datetime.now().astimezone()
    now_iso = now.isoformat()
    logging.debug(f"Ejecutando: get_current_datetime -> {now_iso}") 
    return {"status": "success", "current_datetime_iso": now_iso}

def create_calendar_event(summary: str, start_time: str, end_time: str,
                          description: str, location: str, attendees: List[str]) -> Dict:
    creds = authenticate_google()
    if not creds: return {"status": "error", "message": "Autenticación requerida."}
    parsed_start = _parse_datetime_str(start_time)
    parsed_end = _parse_datetime_str(end_time)
    if not parsed_start or not parsed_end:
        return {"status": "error", "message": "Formato de fecha/hora inválido. Usar formato ISO 8601."}
    try:
        service = build('calendar', 'v3', credentials=creds)
        attendees_list = attendees if isinstance(attendees, list) else []
        event_body = { 'summary': summary, 'description': description, 'location': location,
                       'start': {'dateTime': parsed_start}, 'end': {'dateTime': parsed_end},
                       'attendees': [{'email': email} for email in attendees_list] }
        logging.debug(f"Ejecutando: Crear evento '{summary}'") 
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        event_id = created_event.get('id')
        logging.debug(f"Éxito: Evento creado con ID: {event_id}") 
        return { 'status': 'success', 'event_id': event_id, 'htmlLink': created_event.get('htmlLink') }
    except HttpError as error:
        logging.error(f"Fallo API Google (crear evento): {error.resp.status} {error.reason}")
        return {"status": "error", "message": f"Error API: {error.resp.status} {error.reason}"}
    except Exception as e:
        logging.error(f"Fallo inesperado (crear evento): {e}", exc_info=True)
        return {"status": "error", "message": "Error inesperado del servidor."}

def list_calendar_events(time_min: str, time_max: str, max_results: int) -> Dict:
    """Lista eventos del calendario. Requiere todos los argumentos."""
    creds = authenticate_google()
    if not creds: return {"status": "error", "message": "Autenticación requerida."}

    parsed_time_min = _parse_datetime_str(time_min) 
    parsed_time_max = _parse_datetime_str(time_max)
    safe_max_results = max(1, max_results) if isinstance(max_results, int) else 10 

    if not parsed_time_min or not parsed_time_max:
        return {"status": "error", "message": "Formato de fecha/hora inválido para rango. Usar ISO 8601."}

    try:
        service = build('calendar', 'v3', credentials=creds)
        logging.debug(f"Ejecutando: Listar eventos ({parsed_time_min} a {parsed_time_max}, max:{safe_max_results})") 
        events_result = service.events().list( calendarId='primary', timeMin=parsed_time_min,
                                               timeMax=parsed_time_max, maxResults=safe_max_results,
                                               singleEvents=True, orderBy='startTime' ).execute()
        events = events_result.get('items', [])
        logging.debug(f"Éxito: Encontrados {len(events)} eventos.") 
        return { 'status': 'success', 'events': [ { 'summary': event.get('summary', ''),
                                                    'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                                                    'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
                                                    'description': event.get('description', ''),
                                                    'location': event.get('location', '') } for event in events ] }
    except HttpError as error:
        logging.error(f"Fallo API Google (listar eventos): {error.resp.status} {error.reason}")
        return {"status": "error", "message": f"Error API: {error.resp.status} {error.reason}"}
    except Exception as e:
        logging.error(f"Fallo inesperado (listar eventos): {e}", exc_info=True)
        return {"status": "error", "message": "Error inesperado del servidor."}

# Crear el agente de calendario
calendar_assistant = LlmAgent(
    model=MODEL_NAME,
    name='calendar_assistant',
    instruction='''Eres un asistente especializado **únicamente** en gestionar eventos en Google Calendar.
    Tienes acceso a estas herramientas: `get_current_datetime`, `create_calendar_event`, `list_calendar_events`.

    **TU ÚNICA FUNCIÓN es crear y listar eventos de calendario según las peticiones del usuario.**

    **FLUJO PARA FECHAS RELATIVAS (hoy, ahora, mañana...):**
    1. Si el usuario usa una fecha relativa, PRIMERO llama a `get_current_datetime`.
    2. LUEGO, usa la fecha/hora de la respuesta para calcular los argumentos ISO 8601 (`start_time`, `end_time`, `time_min`, `time_max`) antes de llamar a las herramientas de calendario.
    3. Asume siempre America/Guayaquil (-05:00) si no se especifica otra timezone.

    **REGLAS PARA LLAMAR A LAS HERRAMIENTAS DE CALENDARIO:**
    - `create_calendar_event` y `list_calendar_events` requieren SIEMPRE *todos* sus argumentos.
    - Para `create_calendar_event`: Calcula `start_time`/`end_time` (1h duración por defecto). Usa `description=""`, `location=""`, `attendees=[]` si no se especifican.
    - Para `list_calendar_events`: Calcula `time_min` (inicio día) y `time_max` (fin día). Usa `max_results=10` si no se especifica.

    **MUY IMPORTANTE - DELEGACIÓN DE CONSULTAS:**
    Si el usuario te pide información que NO está relacionada con gestionar eventos de calendario 
    (como "qué es X", "cómo funciona Y", consultas generales de conocimiento), 
    DEBES usar la función `transfer_to_agent` con el parámetro `agent_name="search_assistant"` 
    para transferir esa consulta al agente especializado en búsquedas e información general.

    NO respondas que "no puedes realizar esa solicitud" - usa `transfer_to_agent` en su lugar.
    
    Ejemplos de consultas que debes transferir:
    - "Qué es un dálmata" → transferir a search_assistant
    - "Información sobre París" → transferir a search_assistant
    - "Quién inventó la bombilla" → transferir a search_assistant

    Finalmente, para consultas que SÍ son sobre calendario, responde confirmando la acción 
    realizada o informando del error si ocurrió uno durante la gestión del calendario.''',
    tools=[get_current_datetime, create_calendar_event, list_calendar_events],
)

# Importar el agente de búsqueda desde agent2.py
from . import agent2

# Crear el agente coordinador que usa tanto el agente de calendario como el de búsqueda
root_agent = LlmAgent(
    model=MODEL_NAME,
    name='coordinator_agent',
    description="Agente coordinador que delega solicitudes a agentes especializados",
    instruction="""Eres un asistente que coordina solicitudes entre dos agentes especializados:
    
    1. **calendar_assistant**: Para gestión de eventos de calendario (crear y listar eventos)
    2. **search_assistant**: Para búsquedas de información en Internet y respuestas a preguntas generales
    
    **INSTRUCCIONES DETALLADAS PARA COORDINAR:**
    
    - CALENDARIO: Si el usuario pregunta específicamente sobre crear eventos, listar eventos, o consultar su calendario,
      DEBES transferir la solicitud al agente **calendar_assistant** usando la función `transfer_to_agent`.
      Ejemplos: "Crea un evento", "Qué tengo hoy", "Muestra mi agenda", "Programa una reunión".
      
    - BÚSQUEDA/INFORMACIÓN: Si el usuario pide CUALQUIER información general, definiciones, o hace preguntas
      que NO están relacionadas específicamente con gestionar su calendario personal,
      DEBES transferir la solicitud al agente **search_assistant** usando la función `transfer_to_agent`.
      Ejemplos: "Qué es la IA", "Cuál es la capital de Francia", "Dime sobre machine learning", "Busca información".
    
    - ANÁLISIS DE INTENCIÓN: 
      * Si la solicitud contiene palabras como "crear", "agendar", "programar", "evento", "cita", "mostrar calendario" → calendar_assistant
      * Si la solicitud contiene palabras como "qué es", "definición", "busca", "información", "explica" → search_assistant
    
    - NUNCA intentes responder directamente a las solicitudes.
    - NUNCA ignores una solicitud de búsqueda de información diciéndole al usuario que no puedes hacerlo.
    - Si tienes dudas sobre qué agente usar, elige search_assistant para preguntas generales de información.
    
    Tu ÚNICO trabajo es transferir cada solicitud al agente correcto. No intentes resolver la solicitud tú mismo.
    """,
    sub_agents=[calendar_assistant, agent2.root_agent]
)