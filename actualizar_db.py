import sqlite3
conn = sqlite3.connect("sistema_tesis.db")
try:
    # 0 = Solo Asistencia, 1 = Abre Puerta
    conn.execute("ALTER TABLE usuarios ADD COLUMN acceso_puerta INTEGER DEFAULT 0")
    # Dar permiso al admin por defecto
    conn.execute("UPDATE usuarios SET acceso_puerta = 1 WHERE rol = 'admin'")
    conn.commit()
    print("Base de datos actualizada con permisos de puerta.")
except Exception as e:
    print("La columna ya existía o hubo error:", e)
conn.close()