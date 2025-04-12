# Agente de Calendario con Google ADK

Este proyecto implementa un agente conversacional utilizando el Agent Development Kit (ADK) de Google para interactuar con Google Calendar.

El agente puede:
- Crear eventos en el calendario principal del usuario.
- Listar eventos existentes.
- Manejar la autenticación OAuth 2.0 con la API de Google Calendar.

## Requisitos
- Python 3.10 o superior
- Dependencias listadas en `requirements.txt`
- Credenciales de API de Google (ver archivo `.env`)

## Configuración
1. Crea un archivo `.env` en la raíz del proyecto (ver ejemplo en este repositorio).
2. Instala las dependencias:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
