from google.adk.agents.llm_agent import LlmAgent
import os
import logging
from dotenv import load_dotenv
from . import agent as calendar_agent_module
from . import agent2 as search_agent_module

# Cargar variables de entorno
load_dotenv()

# Configuración del modelo
MODEL_NAME = os.getenv('MODEL_NAME')

# Referencia a los agentes especializados
calendar_agent = calendar_agent_module.root_agent
search_agent = search_agent_module.root_agent

# Crear el agente coordinador que tiene como subagentes a los agentes especializados
root_agent = LlmAgent(
    model=MODEL_NAME,
    name='coordinator_agent',
    description="Agente coordinador que delega solicitudes a agentes especializados",
    instruction="""Eres un asistente que coordina solicitudes entre dos agentes especializados:
    
    1. **calendar_assistant**: Para gestión de eventos de calendario (crear y listar eventos)
    2. **search_assistant**: Para búsquedas de información en Internet
    
    **INSTRUCCIONES IMPORTANTES:**
    
    - Para solicitudes relacionadas con **calendario** (crear eventos, listar eventos, consultar horarios), 
      transfiere la solicitud al agente **calendar_assistant** usando la función `transfer_to_agent`.
      
    - Para solicitudes relacionadas con **búsqueda de información en internet**, transfiere la solicitud 
      al agente **search_assistant** usando la función `transfer_to_agent`.
    
    - Tu tarea principal es determinar cuál de los dos agentes debe manejar cada solicitud.
    
    - No intentes responder directamente a las solicitudes - tu único rol es transferir 
      la solicitud al agente especializado correcto.
    
    - Si la solicitud es ambigua, pregunta al usuario si quiere gestionar su calendario
      o buscar información en internet.
    """,
    sub_agents=[calendar_agent, search_agent]
)
