# agents/coordinator.py
import logging
from dotenv import load_dotenv

from agents import calendar_agent, search_agent
from config import MODEL_NAME

load_dotenv()

calendar_agent_instance = calendar_agent.root_agent
search_agent_instance = search_agent.root_agent

root_agent = calendar_agent_instance.__class__(
    model=MODEL_NAME,
    name='coordinator_agent',
    description="Agente coordinador que delega solicitudes a agentes especializados.",
    instruction="""Eres un asistente coordinador que decide a qué agente delegar una solicitud basándote en las siguientes reglas:
1. Si la consulta incluye términos relacionados con el "calendario", "mi calendario", "eventos", etc., transfiérela al agente calendar_assistant, que gestiona la creación y listado de eventos.
2. Si la consulta es de tipo informativo (por ejemplo, "noticias", "resumen", "información general") sin relación con datos personales, transfiérela al agente search_assistant.
3. Si la intención no es clara o la consulta es ambigua, pregunta al usuario que detalle qué acción desea realizar.

Asegúrate de analizar las palabras clave en la entrada del usuario para asignar la solicitud al agente adecuado.
""",
    sub_agents=[calendar_agent_instance, search_agent_instance],
)
