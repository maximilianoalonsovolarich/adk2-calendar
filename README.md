# Agente de Calendario con Google ADK

Este proyecto implementa un agente conversacional utilizando el Agent Development Kit (ADK) de Google para interactuar con Google Calendar.

El agente puede:
*   Crear eventos en el calendario principal del usuario.
*   Listar eventos existentes del calendario principal.
*   Manejar la autenticación OAuth 2.0 con la API de Google Calendar.

## Requisitos

*   Python 3.10 o superior
*   Dependencias listadas en `requirements.txt`
*   Credenciales de API de Google (ver Configuración)

## Configuración

1.  **Proyecto Google Cloud:**
    *   Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com/).
    *   Habilita la **API de Google Calendar**.
    *   Ve a "APIs y servicios" -> "Credenciales".
    *   Crea un "ID de cliente de OAuth 2.0".
        *   Selecciona "Aplicación de escritorio" como tipo de aplicación.
        *   Descarga el archivo JSON de credenciales. **Renómbralo a `client_secrets.json`** y guárdalo en la raíz del proyecto.
    *   Crea una **Clave de API** para acceder a los modelos de Google AI (Gemini). Cópiala.

2.  **Archivo `.env`:**
    *   Crea un archivo llamado `.env` en la raíz del proyecto.
    *   Añade las siguientes líneas, reemplazando los valores:
        ```dotenv
        GOOGLE_CLIENT_SECRETS_PATH=client_secrets.json
        GOOGLE_CREDENTIALS_PATH=credentials.json
        GOOGLE_API_KEY=TU_CLAVE_API_DE_GOOGLE_AI
        MODEL_NAME=gemini-2.0-flash # O el modelo compatible que prefieras
        ```
    *   `GOOGLE_CREDENTIALS_PATH` es el archivo donde se guardarán los tokens de usuario después de la autenticación (se crea automáticamente).

3.  **Dependencias:**
    *   Crea un entorno virtual (recomendado):
        ```bash
        python -m venv .venv
        source .venv/bin/activate # Linux/macOS
        # .venv\Scripts\activate # Windows
        ```
    *   Instala las dependencias:
        ```bash
        pip install -r requirements.txt
        ```

## Uso

1.  Ejecuta el agente desde la terminal:
    ```bash
    python main.py
    ```
2.  **Primera ejecución:**
    *   El script detectará que no hay credenciales de usuario guardadas.
    *   Te pedirá que visites una URL en tu navegador.
    *   Inicia sesión con tu cuenta de Google y autoriza el acceso a tu calendario.
    *   Copia la URL completa a la que te redirige el navegador después de autorizar.
    *   Pega esa URL en la terminal cuando el script lo solicite.
    *   Las credenciales se guardarán en `credentials.json` para futuras ejecuciones.
3.  **Interactúa con el agente:**
    *   Puedes pedirle que cree eventos:
        *   "Crea un evento para mañana a las 3pm llamado Reunión de equipo"
        *   "Agenda una cita para el viernes a las 10:00 con descripción 'Revisión proyecto'"
        *   "Crea un evento hoy a las 15:00"
    *   Puedes pedirle que liste eventos:
        *   "Muéstrame los eventos de hoy"
        *   "Qué tengo agendado para mañana?"
        *   "Lista los próximos 5 eventos"
    *   Escribe `salir` para terminar.

## Archivos Principales

*   `main.py`: Contiene el código principal del agente, las herramientas y el flujo de ejecución.
*   `requirements.txt`: Lista las dependencias de Python.
*   `.env`: Almacena las claves de API y configuración (¡No subir a Git!).
*   `client_secrets.json`: Contiene los secretos del cliente OAuth descargados de Google Cloud (¡No subir a Git!).
*   `credentials.json`: Almacena los tokens de acceso/refresco del usuario después de la autenticación (¡No subir a Git!).
*   `.gitignore`: Especifica los archivos que Git debe ignorar. 