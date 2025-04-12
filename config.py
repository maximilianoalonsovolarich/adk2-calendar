# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Rutas y claves de API
GOOGLE_CLIENT_SECRETS_PATH = os.getenv("GOOGLE_CLIENT_SECRETS_PATH", "client_secrets.json")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

# Scopes para Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Nivel de logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
