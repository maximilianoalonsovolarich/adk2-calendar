#!/usr/bin/env python3
import os
import sys
import subprocess

# Ejecuta "adk web" mediante subprocess
try:
    # Ejecutamos el comando adk web y redirigimos la salida al terminal.
    subprocess.run(["adk", "web"], check=True)
except subprocess.CalledProcessError as e:
    sys.exit(f"Error al ejecutar 'adk web': {e}")
