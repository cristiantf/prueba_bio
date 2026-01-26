import sqlite3
from werkzeug.security import generate_password_hash
import config

def reset_password():
    """
    Este script actualiza FORZOSAMENTE la contraseña del usuario 'admin'
    a la que se especifique en la variable 'nueva_password'.
    """
    usuario_objetivo = 'admin'
    nueva_password = 'istae123A*'
    
    print(f"--- INICIANDO REINICIO DE CONTRASEÑA PARA EL USUARIO '{usuario_objetivo}' ---")
    
    try:
        # Genera el hash de la nueva contraseña
        nuevo_hash = generate_password_hash(nueva_password, method='pbkdf2:sha256')
        
        conn = sqlite3.connect(config.DB_NAME)
        cursor = conn.cursor()

        # Busca al usuario para asegurarse de que existe
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (usuario_objetivo,))
        usuario = cursor.fetchone()

        if usuario:
            # Si el usuario existe, actualiza su contraseña
            cursor.execute("UPDATE usuarios SET password = ? WHERE username = ?", (nuevo_hash, usuario_objetivo))
            conn.commit()
            print(f"✅ ¡Éxito! La contraseña de '{usuario_objetivo}' ha sido cambiada a '{nueva_password}'.")
        else:
            # Si no existe, informa al usuario.
            # El usuario admin se creará con la nueva contraseña la próxima vez que inicie la app principal.
            print(f"ℹ️  El usuario '{usuario_objetivo}' no existe en la base de datos.")
            print("La próxima vez que inicies la aplicación principal, se creará automáticamente con la nueva contraseña.")
            
        conn.close()

    except sqlite3.Error as e:
        print(f"❌ ERROR: Ocurrió un error con la base de datos: {e}")
    except Exception as e:
        print(f"❌ ERROR: Ocurrió un error inesperado: {e}")

if __name__ == '__main__':
    reset_password()
