# --- CONFIGURACIÓN CENTRALIZADA ---

# Clave secreta para la sesión de Flask. Cambia esto por una cadena aleatoria y compleja.
# Puedes generar una con: python -c 'import secrets; print(secrets.token_hex(16))'
SECRET_KEY = 'tesis_secreta'

# --- Base de Datos ---
DB_NAME = "sistema_tesis.db"

# --- Dispositivos en Red ---
# IP del terminal biométrico Hikvision
IP_BIO = '192.168.1.22'
USER_BIO = 'admin'
PASS_BIO = 'istae1804A' # La contraseña de tu dispositivo

# IP del microcontrolador NodeMCU que controla la puerta
IP_NODE = 'puerta-tesis.local'
TOKEN_NODE = 'istae1805A' # Debe coincidir con el token en el código de Arduino/NodeMCU

# --- URLs de API (se construyen a partir de las IPs) ---
URL_STREAM_BIO = f'http://{IP_BIO}/ISAPI/Event/notification/alertStream'
