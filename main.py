import os
import pickle
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil import parser

from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types
import json
import asyncio
import google.generativeai as genai
import traceback

# Configuración de logging principal (nivel WARNING para producción)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Reducir verbosidad de bibliotecas (ya está bien en WARNING/ERROR)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING) 
logging.getLogger('google.auth.transport.requests').setLevel(logging.WARNING)
logging.getLogger('google.adk').setLevel(logging.WARNING)
logging.getLogger('google.generativeai').setLevel(logging.WARNING)

load_dotenv()

# Configuración de Gemini
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    logging.error("GOOGLE_API_KEY no está configurada en el archivo .env")
    exit("Error crítico: Falta GOOGLE_API_KEY.")
genai.configure(api_key=api_key)

# Configuración de OAuth2
CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
CLIENT_SECRETS_PATH = os.getenv('GOOGLE_CLIENT_SECRETS_PATH', 'client_secrets.json')
MODEL_NAME = os.getenv('MODEL_NAME', 'gemini-2.0-flash')
SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_google() -> Optional[Credentials]:
    """Autentica al usuario con Google Calendar API usando OAuth 2.0."""
    creds = None
    if os.path.exists(CREDENTIALS_PATH):
        try:
            with open(CREDENTIALS_PATH, 'rb') as token_file:
                creds = pickle.load(token_file)
            # Podemos quitar este log o dejarlo en INFO si se considera útil al inicio
            # logging.info(f"Credenciales válidas cargadas desde {CREDENTIALS_PATH}") 
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
                        # logging.info(f"Archivo de credenciales inválido eliminado: {CREDENTIALS_PATH}") # Ya no es necesario loggear esto
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

    # Solo retornar si son válidas al final
    if creds and creds.valid:
        return creds
    else:
        # Si llegamos aquí sin creds válidas después de intentar todo, retornamos None
        logging.warning("No se pudieron obtener credenciales válidas.")
        return None

def _parse_datetime_str(datetime_str: str, default_tz=timezone.utc) -> Optional[str]:
    """Intenta parsear una cadena de fecha/hora a formato ISO, añadiendo UTC si no tiene timezone."""
    if not datetime_str: return None
    try:
        dt = parser.parse(datetime_str)
        # Si no tiene información de timezone, asumir UTC (o podríamos usar una local)
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
    # Cambiar a DEBUG
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
        # Cambiar a DEBUG
        logging.debug(f"Ejecutando: Crear evento '{summary}'") 
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        event_id = created_event.get('id')
        # Cambiar a DEBUG
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

    # Parsear y validar fechas/max_results (ahora siempre esperados)
    parsed_time_min = _parse_datetime_str(time_min) 
    parsed_time_max = _parse_datetime_str(time_max)
    # Asumir que max_results es un int válido (instrucción al LLM)
    safe_max_results = max(1, max_results) if isinstance(max_results, int) else 10 

    if not parsed_time_min or not parsed_time_max:
        return {"status": "error", "message": "Formato de fecha/hora inválido para rango. Usar ISO 8601."}

    try:
        service = build('calendar', 'v3', credentials=creds)
        # Usar directamente los valores parseados/validados
        # Cambiar a DEBUG
        logging.debug(f"Ejecutando: Listar eventos ({parsed_time_min} a {parsed_time_max}, max:{safe_max_results})") 
        events_result = service.events().list( calendarId='primary', timeMin=parsed_time_min,
                                               timeMax=parsed_time_max, maxResults=safe_max_results,
                                               singleEvents=True, orderBy='startTime' ).execute()
        events = events_result.get('items', [])
        # Cambiar a DEBUG
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

# Agente (Instrucciones más estrictas)
calendar_agent = LlmAgent(
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

    **IMPORTANTE:** Si el usuario te pide realizar cualquier otra tarea que no sea crear o listar eventos de calendario (ej: cálculos matemáticos, preguntas generales, etc.), **debes responder educadamente que no puedes realizar esa solicitud**, ya que tu única función es gestionar el calendario.

    Finalmente, responde al usuario confirmando la acción realizada o informando del error si ocurrió uno durante la gestión del calendario.''',
    tools=[get_current_datetime, create_calendar_event, list_calendar_events],
)

async def async_main():
    session_service = InMemorySessionService()
    artifacts_service = InMemoryArtifactService()
    session = session_service.create_session(app_name='calendar_app', user_id='user')
    runner = Runner(app_name='calendar_app', agent=calendar_agent,
                    artifact_service=artifacts_service, session_service=session_service)
    
    # Mantener estos INFO iniciales
    logging.info("Bienvenido al Asistente de Google Calendar")
    logging.info("Verificando credenciales de Google Calendar...")
    if not authenticate_google():
        logging.error("No se pudo autenticar con Google Calendar. Las herramientas de calendario no funcionarán.")
    else:
        logging.info("Autenticación con Google Calendar verificada.")
        
    while True:
        try:
            query = input("\n¿Qué te gustaría hacer? (o 'salir' para terminar): ")
            if query.lower() == 'salir':
                logging.info("Saliendo del asistente.") # Mantener este INFO
                break
            
            content = types.Content(role='user', parts=[types.Part(text=query)])
            events_async = runner.run_async(session_id=session.id, user_id='user', new_message=content)
            
            final_response_text = None
            async for event in events_async:
                # Quitar logs internos del bucle
                if event.is_final_response():
                    if hasattr(event, 'content') and hasattr(event.content, 'parts'):
                         for part in event.content.parts:
                              if hasattr(part, 'text') and part.text:
                                   final_response_text = part.text
                                   break 
                    break 
            
            if final_response_text:
                print(f"\nRespuesta: {final_response_text}")
            else:
                logging.warning("La ejecución del agente terminó sin una respuesta final de texto.")

        except KeyboardInterrupt:
            print("\nSaliendo...")
            break
        except Exception as e:
             logging.error(f"Error durante la interacción: {e}", exc_info=True)
             print("\nOcurrió un error inesperado. Por favor, intenta de nuevo.")

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except Exception as e:
        logging.critical(f"Error fatal al iniciar el programa: {e}")
        traceback.print_exc()
