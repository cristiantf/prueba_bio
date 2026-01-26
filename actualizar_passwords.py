import sqlite3
from werkzeug.security import generate_password_hash
import config  # Importa la configuración para obtener el nombre de la BD

def migrar_passwords():
    """
    Este script actualiza las contraseñas en texto plano a formato hasheado (pbkdf2:sha256).
    Es seguro ejecutarlo múltiples veces; solo afectará a las contraseñas que no estén hasheadas.
    """
    print("--- INICIANDO MIGRACIÓN DE CONTRASEÑAS ---")
    
    try:
        conn = sqlite3.connect(config.DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Selecciona todos los usuarios para revisar sus contraseñas
        cursor.execute("SELECT id, username, password FROM usuarios")
        usuarios = cursor.fetchall()

        if not usuarios:
            print("No se encontraron usuarios en la base de datos.")
            return

        usuarios_actualizados = 0
        for usuario in usuarios:
            password_actual = usuario['password']
            
            # Revisa si la contraseña ya parece estar hasheada
            # El método por defecto de Werkzeug incluye '$' en el hash.
            if password_actual and '$' in password_actual and password_actual.startswith('pbkdf2:sha256'):
                print(f"✔️ El usuario '{usuario['username']}' ya tiene una contraseña hasheada. Omitiendo.")
                continue

            # Si no está hasheada, la hashea y actualiza
            print(f"⚠️  El usuario '{usuario['username']}' tiene una contraseña en texto plano. Actualizando...")
            
            # Genera el nuevo hash
            nuevo_hash = generate_password_hash(password_actual, method='pbkdf2:sha256')
            
            # Actualiza la base de datos
            cursor.execute("UPDATE usuarios SET password = ? WHERE id = ?", (nuevo_hash, usuario['id']))
            usuarios_actualizados += 1

        conn.commit()
        conn.close()

        print("\n--- MIGRACIÓN COMPLETADA ---")
        if usuarios_actualizados > 0:
            print(f"✅ Se actualizaron las contraseñas de {usuarios_actualizados} usuario(s).")
        else:
            print("✅ No se necesitaron actualizaciones. Todas las contraseñas ya estaban seguras.")

    except sqlite3.Error as e:
        print(f"❌ ERROR: Ocurrió un error con la base de datos: {e}")
    except Exception as e:
        print(f"❌ ERROR: Ocurrió un error inesperado: {e}")

if __name__ == '__main__':
    migrar_passwords()
