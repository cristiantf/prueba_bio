from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import biometrico_driver as bio
import threading
import sqlite3
import pandas as pd
import io

from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tesis_secreta' # Clave para las sesiones

# --- FILTRO JINJA PERSONALIZADO ---
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y %H:%M'):
    if value == 'now':
        return datetime.now().strftime(format)
    if isinstance(value, str):
        # Intenta convertir el string a datetime si es necesario
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value # Devuelve el valor original si no se puede convertir
    return value.strftime(format)

# --- CONFIGURACIÓN FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelo de Usuario para Flask-Login
class User(UserMixin):
    def __init__(self, id, username, rol, nombre, bio_id):
        self.id = id
        self.username = username
        self.rol = rol
        self.nombre = nombre
        self.bio_id = bio_id

@login_manager.user_loader
def load_user(user_id):
    conn = bio.get_db_connection()
    u = conn.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if u: return User(u['id'], u['username'], u['rol'], u['nombre'], u['biometric_id'])
    return None

# --- INICIALIZACIÓN ---
bio.init_db()
threading.Thread(target=bio.iniciar_escucha_background, daemon=True).start()

# --- RUTAS DE AUTENTICACIÓN ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        
        conn = bio.get_db_connection()
        usuario = conn.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (user, pw)).fetchone()
        conn.close()
        
        if usuario:
            user_obj = User(usuario['id'], usuario['username'], usuario['rol'], usuario['nombre'], usuario['biometric_id'])
            login_user(user_obj)
            if usuario['rol'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('docente_dashboard'))
        else:
            flash('Usuario o contraseña incorrectos')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- PANEL ADMIN ---
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.rol != 'admin': return redirect(url_for('docente_dashboard'))
    
    conn = bio.get_db_connection()
    docentes = conn.execute("SELECT * FROM usuarios WHERE rol='docente'").fetchall()
    
    # Obtener logs con nombres
    query_logs = '''
        SELECT l.fecha, l.usuario_id, u.nombre, l.tipo_evento 
        FROM logs l 
        LEFT JOIN usuarios u ON l.usuario_id = u.biometric_id 
        ORDER BY l.id DESC LIMIT 20
    '''
    logs = conn.execute(query_logs).fetchall()
    conn.close()
    return render_template('admin.html', docentes=docentes, logs=logs)

@app.route('/crear_docente', methods=['POST'])
@login_required
def crear_docente():
    if current_user.rol != 'admin': return redirect(url_for('login'))
    
    nombre = request.form['nombre']
    bio_id = request.form['bio_id']
    user = request.form['username']
    pw = request.form['password']
    
    try:
        conn = bio.get_db_connection()
        conn.execute("INSERT INTO usuarios (biometric_id, nombre, username, password, rol) VALUES (?, ?, ?, ?, 'docente')",
                     (bio_id, nombre, user, pw))
        conn.commit()
        conn.close()
        flash('Docente creado correctamente', 'success')
    except Exception as e:
        flash(f'Error: El ID o Usuario ya existe. {e}', 'error')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/abrir_puerta')
@login_required
def admin_abrir():
    if current_user.rol != 'admin': return redirect(url_for('login'))
    exito, msg = bio.abrir_puerta_remota(f"Admin: {current_user.nombre}")
    flash(msg, 'success' if exito else 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/eliminar_docente/<int:id>')
@login_required
def eliminar_docente(id):
    if current_user.rol != 'admin': return redirect(url_for('login'))
    try:
        conn = bio.get_db_connection()
        conn.execute("DELETE FROM usuarios WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        flash('Docente eliminado correctamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar: {e}', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/editar_docente/<int:id>')
@login_required
def editar_docente(id):
    if current_user.rol != 'admin': return redirect(url_for('login'))
    
    conn = bio.get_db_connection()
    docente = conn.execute("SELECT * FROM usuarios WHERE id = ?", (id,)).fetchone()
    conn.close()
    
    if docente:
        return render_template('editar_docente.html', docente=docente)
    else:
        flash('Docente no encontrado', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/actualizar_docente', methods=['POST'])
@login_required
def actualizar_docente():
    if current_user.rol != 'admin': return redirect(url_for('login'))
    
    docente_id = request.form['docente_id']
    nombre = request.form['nombre']
    bio_id = request.form['bio_id']
    user = request.form['username']
    pw = request.form.get('password') # Usamos .get para que no falle si no está
    
    try:
        conn = bio.get_db_connection()
        if pw: # Si el campo de contraseña no está vacío
            conn.execute("UPDATE usuarios SET biometric_id = ?, nombre = ?, username = ?, password = ? WHERE id = ?",
                         (bio_id, nombre, user, pw, docente_id))
        else: # Si está vacío, no actualizamos la contraseña
            conn.execute("UPDATE usuarios SET biometric_id = ?, nombre = ?, username = ? WHERE id = ?",
                         (bio_id, nombre, user, docente_id))
        conn.commit()
        conn.close()
        flash('Docente actualizado correctamente', 'success')
    except Exception as e:
        flash(f'Error al actualizar: {e}', 'error')
        
    return redirect(url_for('admin_dashboard'))


# --- API ENDPOINTS ---
@app.route('/api/logs')
@login_required
def api_logs():
    if current_user.rol != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    query_logs = '''
        SELECT l.id, l.fecha, l.usuario_id, u.nombre, l.tipo_evento, l.origen 
        FROM logs l 
        LEFT JOIN usuarios u ON l.usuario_id = u.biometric_id 
        ORDER BY l.id DESC LIMIT 20
    '''
    conn = bio.get_db_connection()
    # Convertir las filas a diccionarios
    logs = [dict(row) for row in conn.execute(query_logs).fetchall()]
    conn.close()
    
    return jsonify(logs)


# --- REPORTES EXCEL ---
@app.route('/descargar_reporte')
@login_required
def descargar_reporte():
    if current_user.rol != 'admin': return redirect(url_for('login'))
    
    # Filtros
    fecha_ini = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    docente_id = request.args.get('docente_id')
    
    query = "SELECT l.fecha, l.usuario_id, u.nombre, l.tipo_evento, l.origen FROM logs l LEFT JOIN usuarios u ON l.usuario_id = u.biometric_id WHERE 1=1"
    params = []
    
    if fecha_ini:
        query += " AND l.fecha >= ?"
        params.append(fecha_ini + " 00:00:00")
    if fecha_fin:
        query += " AND l.fecha <= ?"
        params.append(fecha_fin + " 23:59:59")
    if docente_id and docente_id != 'todos':
        query += " AND l.usuario_id = ?"
        params.append(docente_id)
        
    conn = bio.get_db_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    # Generar Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
    output.seek(0)
    
    return send_file(output, download_name="reporte_asistencia.xlsx", as_attachment=True)

# --- PANEL DOCENTE ---
@app.route('/docente')
@login_required
def docente_dashboard():
    # Solo ve sus propios logs
    conn = bio.get_db_connection()
    logs = conn.execute("SELECT * FROM logs WHERE usuario_id = ? ORDER BY id DESC LIMIT 10", (current_user.bio_id,)).fetchall()
    conn.close()
    return render_template('docente.html', logs=logs)

@app.route('/docente/abrir_puerta')
@login_required
def docente_abrir():
    exito, msg = bio.abrir_puerta_remota(current_user.nombre)
    flash(msg, 'success' if exito else 'error')
    return redirect(url_for('docente_dashboard'))

@app.route('/docente/marcar_web')
@login_required
def docente_marcar():
    # Simula una marcación manual desde la web
    bio.guardar_log("Ahora", current_user.bio_id, "ASISTENCIA WEB", "Panel Web")
    flash("Asistencia registrada manualmente", "success")
    return redirect(url_for('docente_dashboard'))

# --- PERFIL DE USUARIO ---
@app.route('/perfil')
@login_required
def perfil():
    return render_template('cambiar_password.html')

@app.route('/actualizar_password', methods=['POST'])
@login_required
def actualizar_password():
    current_pw = request.form['current_password']
    new_pw = request.form['new_password']
    confirm_pw = request.form['confirm_password']

    # Verificar que la contraseña nueva y la confirmación coinciden
    if new_pw != confirm_pw:
        flash('La nueva contraseña y su confirmación no coinciden.', 'error')
        return redirect(url_for('perfil'))

    # Verificar la contraseña actual del usuario
    conn = bio.get_db_connection()
    user = conn.execute("SELECT password FROM usuarios WHERE id = ?", (current_user.id,)).fetchone()
    
    if user and user['password'] == current_pw:
        # Si la contraseña actual es correcta, actualizarla
        conn.execute("UPDATE usuarios SET password = ? WHERE id = ?", (new_pw, current_user.id))
        conn.commit()
        conn.close()
        flash('Contraseña actualizada correctamente.', 'success')
        # Redirigir al dashboard correspondiente
        if current_user.rol == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('docente_dashboard'))
    else:
        # Si la contraseña actual es incorrecta
        conn.close()
        flash('La contraseña actual es incorrecta.', 'error')
        return redirect(url_for('perfil'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)