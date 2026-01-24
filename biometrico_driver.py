import requests
from requests.auth import HTTPDigestAuth
import json
import sqlite3
import time
import threading
from datetime import datetime

# --- CONFIGURACIÓN ---
IP = '192.168.100.22'
USER = 'admin'
PASS = 'istae1804A'
DB_NAME = "logs.db"
URL_STREAM = f'http://{IP}/ISAPI/Event/notification/alertStream'

# --- BASE DE DATOS ---
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            usuario_id TEXT,
            tipo_evento TEXT,
            origen TEXT
        )
    ''')
    conn.commit()
    conn.close()

def guardar_log(fecha, uid, evento, origen):
    try:
        if fecha == "Ahora":
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        conn = get_db_connection()
        conn.execute("INSERT INTO logs (fecha, usuario_id, tipo_evento, origen) VALUES (?, ?, ?, ?)",
                     (fecha, uid, evento, origen))
        conn.commit()
        conn.close()
        print(f"✅ REGISTRADO EN BD: {uid} | {evento}")
    except Exception as e:
        print(f"⚠️ Error escribiendo en BD: {e}")

# --- CONTROL PUERTA ---
def abrir_puerta_remota():
    url = f'http://{IP}/ISAPI/AccessControl/RemoteControl/door/1'
    xml_cmd = "<RemoteControlDoor xmlns='http://www.isapi.org/ver20/XMLSchema' version='2.0'><cmd>open</cmd></RemoteControlDoor>"
    headers = {'Content-Type': 'application/xml'}
    try:
        r = requests.put(url, auth=HTTPDigestAuth(USER, PASS), data=xml_cmd, headers=headers, timeout=5)
        if r.status_code == 200:
            guardar_log("Ahora", "WEB-ADMIN", "APERTURA REMOTA", "App Web")
            return True, "Puerta Abierta"
        return False, f"Error: {r.status_code}"
    except Exception as e:
        return False, f"Error conexión: {e}"

# --- MONITOR (CORREGIDO CON CONTADOR DE LLAVES) ---
def iniciar_escucha_background():
    print(f"📡 CONECTANDO AL BIOMÉTRICO ({IP})...")
    
    while True:
        try:
            with requests.get(URL_STREAM, auth=HTTPDigestAuth(USER, PASS), stream=True, timeout=90) as r:
                if r.status_code == 200:
                    print("🔵 Conexión establecida. Esperando huellas...")
                    
                    buffer = ""
                    llaves_abiertas = 0
                    capturando = False
                    
                    # Leemos caracter por caracter para no perder nada
                    for chunk in r.iter_content(chunk_size=1):
                        if chunk:
                            char = chunk.decode('utf-8', errors='ignore')
                            
                            # Detectar inicio de JSON
                            if char == '{':
                                if not capturando:
                                    capturando = True
                                    buffer = ""
                                llaves_abiertas += 1
                            
                            if capturando:
                                buffer += char
                                
                                if char == '}':
                                    llaves_abiertas -= 1
                                    
                                    # Si las llaves llegan a cero, tenemos un JSON completo
                                    if llaves_abiertas == 0:
                                        procesar_json(buffer)
                                        capturando = False
                                        buffer = ""
                else:
                    print(f"⚠️ Error HTTP {r.status_code}. Reintentando...")
                    time.sleep(5)
        except Exception as e:
            print(f"❌ Conexión caída: {e}. Reconectando en 5s...")
            time.sleep(5)

def procesar_json(json_raw):
    try:
        data = json.loads(json_raw)
        evt = data.get('AccessControllerEvent', {})
        sub = evt.get('subEventType', 0)
        
        # Ignoramos latidos (0) y alarmas irrelevantes
        if sub != 0:
            # Extraer datos
            uid = evt.get('employeeNoString', 'Desconocido')
            fecha_raw = data.get('dateTime', '')
            fecha = fecha_raw.split('+')[0].replace('T', ' ')
            
            # --- DEBUG EN CONSOLA (Para que veas si llega) ---
            print(f"📩 Recibido Evento Tipo {sub} - Usuario: {uid}")

            msg = None
            origen = "Biométrico"

            if sub == 38: msg, origen = "ASISTENCIA CORRECTA", "Huella"
            elif sub == 75: msg, origen = "VERIFICADO", "Huella"
            elif sub == 1: msg, origen = "BOTON SALIDA", "Físico"
            elif sub == 39: msg, origen = "FALLO AUTENTICACIÓN", "Huella"

            if msg:
                guardar_log(fecha, uid, msg, origen)

    except Exception as e:
        # Si el JSON es basura, lo ignoramos
        pass