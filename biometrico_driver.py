import requests
from requests.auth import HTTPDigestAuth
import json
import sqlite3
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
IP = '192.168.1.22'
USER = 'admin'
PASS = 'istae1804A'
DB_NAME = "sistema_tesis.db" # Nuevo nombre para evitar conflictos
URL_STREAM = f'http://{IP}/ISAPI/Event/notification/alertStream'

# --- BASE DE DATOS ---
def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    
    # 1. Tabla de Usuarios (Docentes y Admins)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            biometric_id TEXT UNIQUE,  -- ID en el aparato (ej: "1")
            nombre TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL, -- Para hacer login
            password TEXT NOT NULL,
            rol TEXT DEFAULT 'docente' -- 'admin' o 'docente'
        )
    ''')

    # 2. Tabla de Logs (Asistencias y Puertas)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATETIME,
            usuario_id TEXT,
            tipo_evento TEXT,
            origen TEXT
        )
    ''')

    # CREAR USUARIO ADMIN POR DEFECTO (Si no existe)
    # Usuario: admin | Clave: 1234
    try:
        conn.execute("INSERT INTO usuarios (biometric_id, nombre, username, password, rol) VALUES (?, ?, ?, ?, ?)", 
                     ('999', 'Administrador Principal', 'admin', '1234', 'admin'))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Ya existe
    
    conn.close()

# --- FUNCIONES DE LOGICA ---
def guardar_log(fecha, uid, evento, origen):
    try:
        if fecha == "Ahora": fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db_connection()
        conn.execute("INSERT INTO logs (fecha, usuario_id, tipo_evento, origen) VALUES (?, ?, ?, ?)", (fecha, uid, evento, origen))
        conn.commit()
        conn.close()
        print(f"✅ LOG: {uid} | {evento}")
    except Exception as e:
        print(f"Error Log: {e}")

def abrir_puerta_remota(solicitante):
    url = f'http://{IP}/ISAPI/AccessControl/RemoteControl/door/1'
    xml_cmd = "<RemoteControlDoor xmlns='http://www.isapi.org/ver20/XMLSchema' version='2.0'><cmd>open</cmd></RemoteControlDoor>"
    headers = {'Content-Type': 'application/xml'}
    try:
        r = requests.put(url, auth=HTTPDigestAuth(USER, PASS), data=xml_cmd, headers=headers, timeout=5)
        if r.status_code == 200:
            guardar_log("Ahora", solicitante, "APERTURA REMOTA", "Panel Web")
            return True, "Puerta Abierta"
        return False, f"Error Biométrico: {r.status_code}"
    except Exception as e:
        return False, f"Error Conexión: {e}"

# --- MONITOR EN SEGUNDO PLANO ---
def iniciar_escucha_background():
    print(f"📡 MONITOR INICIADO ({IP})...")
    while True:
        try:
            with requests.get(URL_STREAM, auth=HTTPDigestAuth(USER, PASS), stream=True, timeout=90) as r:
                if r.status_code == 200:
                    buffer = ""; llaves = 0; capturando = False
                    for chunk in r.iter_content(chunk_size=1):
                        if chunk:
                            char = chunk.decode('utf-8', errors='ignore')
                            if char == '{':
                                if not capturando: capturando = True; buffer = ""
                                llaves += 1
                            if capturando:
                                buffer += char
                                if char == '}':
                                    llaves -= 1
                                    if llaves == 0:
                                        procesar_json(buffer)
                                        capturando = False; buffer = ""
                else:
                    time.sleep(5)
        except:
            time.sleep(5)

def procesar_json(json_raw):
    try:
        data = json.loads(json_raw)
        evt = data.get('AccessControllerEvent', {})
        sub = evt.get('subEventType', 0)
        
        if sub != 0:
            uid = evt.get('employeeNoString', 'Desconocido')
            fecha = data.get('dateTime', '').split('+')[0].replace('T', ' ')
            
            msg = None; origen = "Biométrico"
            if sub == 38: msg, origen = "ASISTENCIA", "Huella"
            elif sub == 75: msg, origen = "VERIFICACIÓN OK", "Huella"
            elif sub == 1: msg, origen = "BOTON SALIDA", "Físico"
            elif sub == 39: msg, origen = "FALLO LOGIN", "Huella"

            if msg: guardar_log(fecha, uid, msg, origen)
    except:
        pass