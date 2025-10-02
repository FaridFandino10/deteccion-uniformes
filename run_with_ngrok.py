import subprocess
import time
import requests
import sys
import os  # noqa: F401

# Cambia esto si ngrok.exe no está en tu PATH
NGROK_PATH = "ngrok"  # o r"C:\ruta\a\ngrok.exe"

# Lanza Flask en segundo plano
flask_proc = subprocess.Popen([sys.executable, "app.py"])

# Espera a que Flask arranque
time.sleep(3)

# Lanza ngrok en segundo plano
ngrok_proc = subprocess.Popen([NGROK_PATH, "http", "5000"])

# Espera a que ngrok arranque
time.sleep(3)

# Obtiene la URL pública de ngrok
try:
    resp = requests.get("http://localhost:4040/api/tunnels")
    public_url = resp.json()["tunnels"][0]["public_url"]
    print(f"\nTu app está disponible en: {public_url}\n")
    print("¡Abre esta URL desde cualquier celular o compártela con los técnicos!")
except Exception as e:
    print("No se pudo obtener la URL pública de ngrok. ¿Está corriendo ngrok correctamente?")
    print(e)

try:
    flask_proc.wait()
except KeyboardInterrupt:
    flask_proc.terminate()
    ngrok_proc.terminate()

    #TOKEN DE NGROK: ngrok config add-authtoken 32v4bC8v68gzcqamrtzWAsqA7qe_3iY6XRibGCUZnSi7ggKTu