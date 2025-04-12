#!/usr/bin/env python3
import sys
import subprocess
from logging_config import configure_logging

configure_logging()  # Configura el logging de acuerdo al entorno

try:
    # Ejecuta "adk web" para iniciar el servidor del ADK
    subprocess.run(["adk", "web"], check=True)
except subprocess.CalledProcessError as e:
    sys.exit(f"Error al ejecutar 'adk web': {e}")
