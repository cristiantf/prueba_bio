from flask import Flask, render_template, jsonify, request
import biometrico_driver as bio
import threading
import sqlite3

app = Flask(__name__)

# Inicializamos la BD al arrancar
bio.init_db()

# Arrancamos el monitor en un Hilo (Thread) para que no bloquee la web
# daemon=True significa que si cierras la app, el hilo muere también
hilo_monitor = threading.Thread(target=bio.iniciar_escucha_background, daemon=True)
hilo_monitor.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/abrir_puerta', methods=['POST'])
def abrir_puerta():
    exito, mensaje = bio.abrir_puerta_remota()
    return jsonify({"success": exito, "message": mensaje})

@app.route('/api/historial')
def obtener_historial():
    """API para obtener datos sin recargar la página"""
    conn = bio.get_db_connection()
    logs = conn.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 50').fetchall()
    conn.close()
    
    # Convertir a lista de diccionarios para JSON
    lista_logs = [dict(ix) for ix in logs]
    return jsonify(lista_logs)

if __name__ == '__main__':
    # use_reloader=False es IMPORTANTE para no duplicar el hilo del monitor
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)