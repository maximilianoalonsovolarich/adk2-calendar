import os
import logging
from dotenv import load_dotenv

from agents import calendar_agent, search_agent

# Cargar variables de entorno
load_dotenv()

MODEL_NAME = os.getenv('MODEL_NAME')

# Referencias a los agentes especializados
calendar_agent_instance = calendar_agent.root_agent
search_agent_instance = search_agent.root_agent

root_agent = calendar_agent_instance.__class__(
    model=MODEL_NAME,
    name='coordinator_agent',
    description="Agente coordinador que delega solicitudes a agentes especializados.",
    instruction="""Eres un asistente coordinador que decide si una solicitud debe ser manejada por:
    
1. **calendar_assistant:** Para gestionar eventos (crear, listar, etc.).
2. **search_assistant:** Para búsquedas de información en internet.

**INSTRUCCIONES:**
- Si la solicitud se relaciona con calendario, transfiérela a `calendar_assistant`.
- Si se trata de información general, transfiérela a `search_assistant`.
- Si la solicitud es ambigua, pregunta al usuario qué acción desea realizar.
""",
    sub_agents=[calendar_agent_instance, search_agent_instance]
)
