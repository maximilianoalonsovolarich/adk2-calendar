from google.adk.agents.llm_agent import LlmAgent
import os
import logging
import requests
import json
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Cargar variables de entorno
load_dotenv()

# Configuración del modelo y API keys
MODEL_NAME = os.getenv('MODEL_NAME')
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')

def brave_search(query: str) -> Dict:
    """
    Realiza una búsqueda en internet usando Brave Search API
    
    Args:
        query (str): La consulta de búsqueda
        
    Returns:
        dict: Resultados de la búsqueda
    """
    if not query:
        return {
            "status": "error",
            "message": "Se requiere una consulta para realizar la búsqueda."
        }
    
    if not BRAVE_API_KEY:
        return {
            "status": "error",
            "message": "No se encontró la API key de Brave. Verifica el archivo .env."
        }
    
    headers = {
        "X-Subscription-Token": BRAVE_API_KEY,
        "Accept": "application/json"
    }
    
    try:
        # Realizar la petición a Brave Search API
        response = requests.get(
            f"https://api.search.brave.com/res/v1/web/search?q={query}&count=5",
            headers=headers
        )
        
        # Verificar si la petición fue exitosa
        if response.status_code == 200:
            data = response.json()
            
            # Extraer los resultados más relevantes
            results = []
            if "web" in data and "results" in data["web"]:
                for result in data["web"]["results"][:5]:  # Limitar a 5 resultados
                    results.append({
                        "title": result.get("title", ""),
                        "description": result.get("description", ""),
                        "url": result.get("url", "")
                    })
            
            return {
                "status": "success",
                "query": query,
                "results": results
            }
        else:
            return {
                "status": "error",
                "message": f"Error de API Brave: {response.status_code}",
                "details": response.text
            }
    except Exception as e:
        logging.error(f"Error al realizar búsqueda en Brave: {e}")
        return {
            "status": "error",
            "message": f"Error inesperado al realizar la búsqueda: {str(e)}"
        }

def search_event_info(event_title: str) -> Dict:
    """
    Busca información en Google sobre un título de evento específico.
    
    Args:
        event_title (str): El título del evento sobre el que buscar información.
        
    Returns:
        dict: Estado de la operación y resultados de la búsqueda.
    """
    if not event_title:
        return {
            "status": "error",
            "message": "Se requiere un título de evento para realizar la búsqueda."
        }
    
    # Registrar la búsqueda
    logging.debug(f"Buscando información sobre el evento: '{event_title}'")
    
    # En un entorno real, aquí utilizaríamos la herramienta google_search para obtener resultados
    # Como google_search es una herramienta para usar dentro del agente y no una función independiente,
    # esta función es principalmente para integración entre agentes
    return {
        "status": "success",
        "query": event_title,
        "message": f"Búsqueda realizada para: {event_title}. Usa esta información dentro del agente."
    }

def find_nearby_events(location: str, date: str) -> Dict:
    """
    Busca eventos cercanos a una ubicación en una fecha específica.
    
    Args:
        location (str): La ubicación donde buscar eventos cercanos.
        date (str): La fecha para la cual buscar eventos.
        
    Returns:
        dict: Estado de la operación y resultados de la búsqueda.
    """
    if not location:
        return {
            "status": "error",
            "message": "Se requiere una ubicación para buscar eventos cercanos."
        }
    
    # Registrar la búsqueda
    logging.debug(f"Buscando eventos cercanos en {location} para {date}")
    
    # Similar a search_event_info, esta función es para integración entre agentes
    return {
        "status": "success",
        "query": f"eventos en {location} {date}",
        "message": f"Búsqueda realizada para eventos en {location} en la fecha {date}."
    }

# Función para usar en el agente como herramienta
def search_info(query: str) -> Dict:
    """
    Busca información sobre un tema específico utilizando Brave Search.
    
    Args:
        query (str): La consulta de búsqueda
        
    Returns:
        dict: Resultados de la búsqueda de Brave
    """
    logging.info(f"Buscando información sobre: '{query}'")
    return brave_search(query)

# Crear y exportar el agente de búsqueda
search_agent = LlmAgent(
    model=MODEL_NAME,
    name='search_assistant',
    description="Asistente especializado en buscar y proporcionar información general usando Brave Search",
    instruction='''Eres un asistente especializado en buscar y proporcionar información sobre temas generales y específicos utilizando Brave Search.
    
    **TU FUNCIÓN PRINCIPAL:**
    Responder preguntas informativas del usuario utilizando búsquedas en internet para obtener información actualizada.
    
    **FLUJO DE TRABAJO:**
    1. Cuando recibas una consulta, PRIMERO usa la herramienta `search_info` con la consulta del usuario.
    2. Analiza los resultados de búsqueda para extraer la información más relevante.
    3. Formula una respuesta completa y estructurada basada en los resultados de la búsqueda.
    4. Cita fuentes cuando sea posible, mencionando de dónde obtuviste la información.
    
    **REGLAS PARA REALIZAR BÚSQUEDAS:**
    - Haz preguntas específicas y claras en tus búsquedas
    - Prioriza información objetiva y verificable
    - Extrae información de múltiples fuentes cuando sea posible
    - Informa al usuario cuando no encuentres información confiable
    
    **FORMATO DE RESPUESTA:**
    Estructura tus respuestas de la siguiente manera:
    1. Proporciona una definición o descripción concisa del tema
    2. Añade detalles importantes o contexto relevante
    3. Incluye datos específicos de los resultados de búsqueda
    4. Si es apropiado, menciona alguna fuente consultada
    
    Mantén tus respuestas claras, directas y útiles, presentando la información de manera conversacional.
    Responde "No pude encontrar información relevante sobre esto" solo si realmente no hay resultados útiles.
    
    Recuerda que tu objetivo es proporcionar información de alta calidad usando Brave Search.
    ''',
    tools=[search_info],
)

# Función que podría ser utilizada por el agente principal (agent.py) para delegar búsquedas al search_agent
def search_context_for_event(event_title: str, location: str = None, date: str = None) -> Dict:
    """
    Función de integración para que el agente principal solicite búsquedas contextuales.
    En una implementación real, esto invocaría al search_agent a través de un flujo de trabajo.
    
    Args:
        event_title (str): Título del evento para buscar información.
        location (str, optional): Ubicación del evento. Predeterminado a None.
        date (str, optional): Fecha del evento. Predeterminado a None.
    
    Returns:
        Dict: Resultados del contexto encontrado (simulado).
    """
    logging.info(f"Agente principal solicitó búsqueda de contexto para '{event_title}'")
    
    # Esta es una versión simulada. En una implementación real, 
    # se utilizaría el search_agent a través de un sistema multiagente
    results = {
        "status": "success",
        "event_title": event_title,
        "context_requested": True,
        "message": f"Contexto para evento '{event_title}' solicitado al agente de búsqueda."
    }
    
    if location:
        results["location_info"] = f"Se incluyó información de ubicación: {location}"
    
    if date:
        results["date_info"] = f"Se incluyó información de fecha: {date}"
    
    return results

# Variable que expone el agente para ser utilizado en un sistema multi-agente
root_agent = search_agent
