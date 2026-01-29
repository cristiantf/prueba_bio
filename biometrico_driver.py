import requests
from requests.auth import HTTPDigestAuth
import json
import sqlite3
import time
from datetime import datetime
from werkzeug.security import generate_password_hash

# --- CONFIGURACIÓN (Importada) ---
import config

# --- BASE DE DATOS ---
def get_db_connection():
    """Establece conexión con la base de datos."""
    conn = sqlite3.connect(config.DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    conn = get_db_connection()
    # Tabla de usuarios con todos los campos necesarios
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            biometric_id TEXT UNIQUE,
            nombre TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT DEFAULT 'docente',
            acceso_puerta INTEGER DEFAULT 0 -- 0=No abre, 1=Sí abre
        )
    ''')
    # Tabla de logs para registrar todos los eventos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATETIME,
            usuario_id TEXT,
            tipo_evento TEXT,
            origen TEXT
        )
    ''')
    
    # Crear admin por defecto si no existe
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone() is None:
        # ¡IMPORTANTE! Se guarda la contraseña hasheada, no en texto plano.
        hashed_password = generate_password_hash('istae123A*', method='pbkdf2:sha256')
        try:
            conn.execute("INSERT INTO usuarios (biometric_id, nombre, username, password, rol, acceso_puerta) VALUES (?, ?, ?, ?, ?, ?)", 
                         ('999', 'Admin Principal', 'admin', hashed_password, 'admin', 1))
            conn.commit()
            print("INFO: Usuario 'admin' con contraseña por defecto 'istae123A*' creado.")
        except sqlite3.IntegrityError:
            # Esto podría pasar en un caso raro de concurrencia
            pass
    conn.close()

# --- FUNCIONES LÓGICAS ---
def guardar_log(fecha, uid, evento, origen):
    """Guarda un evento en la tabla de logs."""
    try:
        if fecha == "Ahora": 
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = get_db_connection()
        conn.execute("INSERT INTO logs (fecha, usuario_id, tipo_evento, origen) VALUES (?, ?, ?, ?)", (fecha, uid, evento, origen))
        conn.commit()
        conn.close()
        print(f"✅ LOG GUARDADO: {uid} | {evento} ({origen})")
    except Exception as e:
        print(f"❌ Error guardando log: {e}")

def abrir_puerta_fisica():
    """
    Envía la señal al NodeMCU para abrir la puerta.
    Utiliza una Sesión para garantizar que la conexión se cierre correctamente.
    """
    url = f"http://{config.IP_NODE}/api/abrir?token={config.TOKEN_NODE}"
    try:
        with requests.Session() as s:
            # Timeout: 2s para conectar, 3s para recibir respuesta
            r = s.get(url, timeout=(2, 3))
        
        if r.status_code == 200:
            print("🔓 PUERTA ABIERTA (Vía NodeMCU)")
            return True
        else:
            print(f"⚠️ NodeMCU respondió con error: {r.status_code} - {r.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error de conexión con NodeMCU ({config.IP_NODE}): {e}")
        return False
    except Exception as e:
        print(f"⚠️ Ocurrió un error inesperado en abrir_puerta_fisica: {e}")
        return False

def abrir_puerta_remota(solicitante):
    """
    Lógica para abrir la puerta desde la App Web (Admin o Docente).
    Registra el log y después intenta abrir la puerta.
    """
    if abrir_puerta_fisica():
        # Solo si la puerta abrió correctamente, se guarda el log
        guardar_log("Ahora", solicitante, "APERTURA WEB", "Panel Web")
        return True, "Puerta Abierta Correctamente"
    else:
        return False, "Error: No se pudo conectar con el módulo de puerta (NodeMCU)"

# --- PROCESAMIENTO INTELIGENTE DE EVENTOS DEL BIOMÉTRICO ---
def verificar_permiso_y_abrir(biometric_id):
    """
    Busca al usuario en la BD por su ID biométrico. 
    Si tiene `acceso_puerta = 1`, manda la señal para abrir el NodeMCU.
    """
    conn = get_db_connection()
    user = conn.execute("SELECT acceso_puerta, nombre FROM usuarios WHERE biometric_id = ?", (biometric_id,)).fetchone()
    conn.close()

    if user:
        if user['acceso_puerta'] == 1:
            print(f"ℹ️  Usuario '{user['nombre']}' tiene permiso. Abriendo puerta...")
            abrir_puerta_fisica()
        else:
            print(f"ℹ️  Usuario '{user['nombre']}' marcó asistencia, pero no tiene permiso de puerta.")
    else:
        print(f"⚠️ ID Biométrico desconocido '{biometric_id}' marcó asistencia.")

def procesar_json(json_raw):
    """
    Decodifica el JSON del biométrico y actúa según el tipo de evento.
    """
    try:
        data = json.loads(json_raw)
        evt = data.get('AccessControllerEvent', {})
        major_evt = evt.get('majorEventType', 0)
        sub_evt = evt.get('subEventType', 0)
        
        # Evento principal 5 = Evento de control de acceso
        if major_evt == 5:
            uid = evt.get('employeeNoString', 'Desconocido')
            fecha_raw = evt.get('time', '')
            fecha = fecha_raw.split('+')[0].replace('T', ' ') if fecha_raw else "Ahora"
            
            # Sub-evento de verificación válida (ej. huella correcta)
            if sub_evt in [1, 38, 75]:
                guardar_log(fecha, uid, "ASISTENCIA", "Huella")
                verificar_permiso_y_abrir(uid)
            # Sub-evento de fallo (ej. huella incorrecta)
            elif sub_evt == 39: 
                guardar_log("Ahora", uid, "FALLO INTENTO", "Huella")

    except Exception as e:
        print(f"❌ Error procesando JSON: {e}\nRaw: {json_raw}")

# --- MONITOR EN SEGUNDO PLANO ---
def iniciar_escucha_background():
    """
    Se conecta al stream de eventos del biométrico y lo escucha indefinidamente.
    Se ejecuta en un hilo separado para no bloquear la app web.
    """
    print(f"📡 ESCUCHANDO BIOMÉTRICO ({config.IP_BIO})...")
    while True:
        try:
            auth = HTTPDigestAuth(config.USER_BIO, config.PASS_BIO)
            with requests.get(config.URL_STREAM_BIO, auth=auth, stream=True, timeout=90) as r:
                
                if r.status_code == 200:
                    print("✅ Conexión al stream de eventos establecida.")
                    buffer = ""; llaves = 0; capturando = False
                    
                    for chunk in r.iter_content(chunk_size=256): # Aumentado chunk_size para eficiencia
                        if chunk:
                            char_chunk = chunk.decode('utf-8', errors='ignore')
                            for char in char_chunk:
                                if char == '{':
                                    if not capturando: 
                                        capturando = True
                                        buffer = ""
                                    llaves += 1
                                
                                if capturando:
                                    buffer += char
                                    if char == '}':
                                        llaves -= 1
                                        if llaves == 0:
                                            procesar_json(buffer)
                                            capturando = False
                elif r.status_code == 401:
                    print("❌ Error de autenticación (401) con el biométrico. Revisa USER_BIO y PASS_BIO en config.py.")
                    time.sleep(30) # Espera más tiempo si la autenticación falla
                else:
                    print(f"⚠️ Stream desconectado (Código: {r.status_code}). Reconectando en 10 segundos...")
                    time.sleep(10)

        except requests.exceptions.ConnectionError as e:
            print(f"❌ Error de conexión con el biométrico ({config.IP_BIO}). Revisa la IP y la red. Reintentando en 15s... Error: {e}")
            time.sleep(15)
        except Exception as e:
            print(f"❌ Error inesperado en el hilo de escucha: {e}. Reconectando en 15s...")
            time.sleep(15)