import os
import logging
import requests
import json
from dotenv import load_dotenv
from typing import Dict

from google.adk.agents.llm_agent import LlmAgent

# Cargar variables de entorno
load_dotenv()

MODEL_NAME = os.getenv('MODEL_NAME')
BRAVE_API_KEY = os.getenv('BRAVE_API_KEY')

def brave_search(query: str) -> Dict:
    """
    Realiza una búsqueda en internet usando Brave Search API.

    Args:
        query (str): La consulta de búsqueda.

    Returns:
        dict: Resultados de la búsqueda.
    """
    if not query:
        return {"status": "error", "message": "Se requiere una consulta para la búsqueda."}
    if not BRAVE_API_KEY:
        return {"status": "error", "message": "Falta la API key de Brave. Verifica el archivo .env."}

    headers = {
        "X-Subscription-Token": BRAVE_API_KEY,
        "Accept": "application/json"
    }

    try:
        response = requests.get(
            f"https://api.search.brave.com/res/v1/web/search?q={query}&count=5",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            results = []
            if "web" in data and "results" in data["web"]:
                for result in data["web"]["results"][:5]:
                    results.append({
                        "title": result.get("title", ""),
                        "description": result.get("description", ""),
                        "url": result.get("url", "")
                    })
            return {"status": "success", "query": query, "results": results}
        else:
            return {"status": "error", "message": f"Error de API Brave: {response.status_code}", "details": response.text}
    except Exception as e:
        logging.error(f"Error durante la búsqueda en Brave: {e}")
        return {"status": "error", "message": f"Error inesperado en la búsqueda: {str(e)}"}

def search_info(query: str) -> Dict:
    """
    Realiza una búsqueda de información utilizando Brave Search.

    Args:
        query (str): La consulta a buscar.

    Returns:
        dict: Resultados de la búsqueda.
    """
    logging.info(f"Buscando información sobre: '{query}'")
    return brave_search(query)

search_assistant = LlmAgent(
    model=MODEL_NAME,
    name='search_assistant',
    description="Asistente especializado en buscar información mediante Brave Search.",
    instruction="""Eres un asistente que busca y proporciona información de temas variados utilizando Brave Search.

**TU FUNCIÓN PRINCIPAL:**
1. Al recibir una consulta, usa la herramienta `search_info` para realizar la búsqueda.
2. Analiza los resultados y formula una respuesta estructurada citando las fuentes.

**REGLAS:**
- Utiliza siempre Brave Search para buscar información actualizada.
- Responde de forma clara, citando las fuentes cuando sea posible.
""",
    tools=[search_info],
)

# Exponer el agente para integración multi-agente
root_agent = search_assistant
