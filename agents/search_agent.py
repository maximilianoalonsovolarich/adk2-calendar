# agents/search_agent.py
import logging
import requests
from typing import Dict
from dotenv import load_dotenv

from google.adk.agents.llm_agent import LlmAgent
from config import MODEL_NAME, BRAVE_API_KEY
from constants import SEARCH_PROMPT

load_dotenv()

def brave_search(query: str) -> Dict:
    if not query:
        return {"status": "error", "message": "Se requiere una consulta para la búsqueda."}
    if not BRAVE_API_KEY:
        return {"status": "error", "message": "Falta la API key de Brave. Verifica el archivo .env."}
    headers = {
        "X-Subscription-Token": BRAVE_API_KEY,
        "Accept": "application/json"
    }
    try:
        response = requests.get(f"https://api.search.brave.com/res/v1/web/search?q={query}&count=5", headers=headers)
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

def summarize_results(results: list) -> str:
    """
    Genera un resumen a partir de una lista de resultados.
    """
    if not results:
        return "No se encontraron resultados para resumir."
    summary_lines = []
    for item in results:
        title = item.get("title", "Sin título")
        description = item.get("description", "")
        # Puedes acortar la descripción si es muy extensa
        summary_lines.append(f"- {title}: {description}")
    return "\n".join(summary_lines)

def search_info(query: str) -> Dict:
    logging.info(f"Buscando información sobre: '{query}'")
    result = brave_search(query)
    # Si la consulta contiene "resumen", se procesa la lista de resultados para sintetizar la información
    if "resumen" in query.lower():
        results = result.get("results", [])
        summary = summarize_results(results)
        return {"status": "success", "query": query, "summary": summary}
    return result

search_assistant = LlmAgent(
    model=MODEL_NAME,
    name='search_assistant',
    description="Asistente especializado en buscar información mediante Brave Search.",
    instruction=SEARCH_PROMPT,
    tools=[search_info],
)

root_agent = search_assistant
