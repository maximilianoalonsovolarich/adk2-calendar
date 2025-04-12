# Agente de Calendario con Google ADK

Este proyecto implementa un agente conversacional utilizando el Agent Development Kit (ADK) de Google para interactuar con Google Calendar.

El agente puede:
* Crear eventos en el calendario principal del usuario.
* Listar eventos existentes.
* Manejar la autenticación OAuth 2.0 con la API de Google Calendar.

## Requisitos

* Python 3.10 o superior
* Dependencias listadas en `requirements.txt`
* Credenciales de API de Google (ver Configuración)

## Configuración

1. **Proyecto Google Cloud:**
   - Sigue los pasos descritos en la documentación para crear credenciales OAuth 2.0 y una clave de API.

2. **Archivo `.env`:**
   - Crea un archivo llamado `.env` en la raíz del proyecto y agrega las siguientes líneas (reemplaza los valores según corresponda):

     ```dotenv
     GOOGLE_CLIENT_SECRETS_PATH=client_secrets.json
     GOOGLE_API_KEY=TU_CLAVE_API_DE_GOOGLE_AI
     MODEL_NAME=gemini-2.0-flash-exp
     BRAVE_API_KEY=TU_BRAVE_API_KEY
     GOOGLE_CREDENTIALS_PATH=credentials.json
     ```

3. **Dependencias:**
   - Crea un entorno virtual (recomendado) e instala las dependencias:
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # Linux/macOS
     # .venv\Scripts\activate   # Windows
     pip install -r requirements.txt
     ```

## Uso

1. Ejecuta el agente desde la terminal:
   ```bash
   python main.py
