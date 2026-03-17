from flask import Flask, request, jsonify, render_template
import mysql.connector
from flask_cors import CORS
import math
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__, template_folder='TEMPLATES', static_folder='static')
CORS(app)

app.config['SECRET_KEY'] = 'mi_clave_secreta_super_segura_2024'  # Cambia esto por una clave segura en producción

# Decorador para verificar token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token faltante'}), 401
        try:
            token = token.split(" ")[1]  # Bearer token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return jsonify({'message': 'Token inválido'}), 401
        return f(*args, **kwargs)
    return decorated

# Ruta para obtener token
@app.route('/token', methods=['GET'])
def get_token():
    # Para simplicidad, devolver un token sin credenciales (en producción, requerir autenticación)
    token = jwt.encode({
        'user': 'consumer',
        'exp': datetime.utcnow() + timedelta(hours=1)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({'token': token})

# Configuración MySQL
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT", 14605)),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        return connection
    except Exception as e:
        print(f"✗ Error conectando a MySQL: {e}")
        return None

# Probar conexión al iniciar
print("Intentando conectar a la base de datos...")
test_conn = get_db_connection()
if test_conn:
    print("✓ Conexión a MySQL exitosa")
    test_conn.close()
else:
    print("✗ Fallo en la conexión a MySQL")

# -------------------------------
# Obtener todos los lugares
# -------------------------------

def _get_all_info():
    connection = get_db_connection()
    if not connection:
        return None, {"error": "No se pudo conectar a la base de datos"}

    cursor = connection.cursor()
    informacion = {
        "ciudades": [],
        "categorias": [],
        "lugares": []
    }

    # Ciudades
    cursor.execute("SELECT nombre FROM ciudades ORDER BY nombre")
    ciudades = cursor.fetchall()
    informacion["ciudades"] = [ciudad[0] for ciudad in ciudades]

    # Categorías
    cursor.execute("SELECT nombre FROM categorias ORDER BY nombre")
    categorias = cursor.fetchall()
    informacion["categorias"] = [categoria[0] for categoria in categorias]

    # Lugares
    cursor.execute("""
        SELECT nombre, descripcion, calificacion 
        FROM lugares 
        ORDER BY nombre
    """)
    lugares = cursor.fetchall()
    informacion["lugares"] = [
        {
            "nombre": lugar[0],
            "descripcion": lugar[1] if lugar[1] else "",
            "calificacion": float(lugar[2]) if lugar[2] else None
        }
        for lugar in lugares
    ]

    cursor.close()
    connection.close()

    return informacion, None

@app.route('/', methods=['GET'])
@token_required
def inicio():
    informacion, error = _get_all_info()
    if error:
        return jsonify(error), 500
    return jsonify(informacion)

@app.route('/web-service', methods=['GET'])
@token_required
def web_service():
    informacion, error = _get_all_info()
    if error:
        return jsonify(error), 500
    return jsonify(informacion)

from flask import render_template

@app.route('/obtener_ciudades', methods=['GET'])
def obtener_ciudades():
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
        cursor = connection.cursor()
        cursor.execute("SELECT id_ciudad, nombre FROM ciudades")
        ciudades = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(list(ciudades))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/obtener_categorias', methods=['GET'])
def obtener_categorias():
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
        cursor = connection.cursor()
        cursor.execute("SELECT id_categoria, nombre FROM categorias")
        categorias = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(list(categorias))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/guardar_lugar', methods=['POST'])
def guardar_lugar():
    try:
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion', '')
        direccion = request.form.get('direccion', '')
        latitud = request.form.get('latitud')
        longitud = request.form.get('longitud')
        id_ciudad = request.form.get('id_ciudad')
        id_categoria = request.form.get('id_categoria')

        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

        cursor = connection.cursor()
        query = """
        INSERT INTO lugares
        (nombre, descripcion, direccion, latitud, longitud, id_ciudad, id_categoria)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(query, (nombre, descripcion, direccion, latitud, longitud, id_ciudad, id_categoria))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"mensaje": "Lugar agregado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/lugares', methods=['GET'])
def api_lugares():
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

        cursor = connection.cursor()
        cursor.execute("""
            SELECT 
                l.id_lugar,
                l.nombre,
                l.descripcion,
                l.direccion,
                l.latitud,
                l.longitud,
                c.nombre AS ciudad,
                c.estado,
                c.pais,
                cat.nombre AS categoria
            FROM lugares l
            LEFT JOIN ciudades c ON l.id_ciudad = c.id_ciudad
            LEFT JOIN categorias cat ON l.id_categoria = cat.id_categoria
            ORDER BY l.nombre
        """)
        
        lugares = cursor.fetchall()
        lugares_json = []
        
        for lugar in lugares:
            lugares_json.append({
                "nombre": lugar[1],
                "descripcion": lugar[2] if lugar[2] else "",
                "direccion": lugar[3] if lugar[3] else "",
                "latitud": float(lugar[4]) if lugar[4] else None,
                "longitud": float(lugar[5]) if lugar[5] else None,
                "ciudad": lugar[6] if lugar[6] else "Sin ciudad",
                "estado": lugar[7] if lugar[7] else "Sin estado",
                "pais": lugar[8] if lugar[8] else "Sin país",
                "categoria": lugar[9] if lugar[9] else "Sin categoría"
            })
        
        cursor.close()
        connection.close()
        return jsonify(lugares_json)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/extraer_informacion', methods=['GET'])
def extraer_informacion():
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

        cursor = connection.cursor()
        informacion = {
            "ciudades": [],
            "categorias": [],
            "lugares": []
        }
        
        # Ciudades
        cursor.execute("SELECT nombre FROM ciudades ORDER BY nombre")
        ciudades = cursor.fetchall()
        informacion["ciudades"] = [ciudad[0] for ciudad in ciudades]
        
        # Categorías
        cursor.execute("SELECT nombre FROM categorias ORDER BY nombre")
        categorias = cursor.fetchall()
        informacion["categorias"] = [categoria[0] for categoria in categorias]
        
        # Lugares
        cursor.execute("""
            SELECT nombre, descripcion, calificacion 
            FROM lugares 
            ORDER BY nombre
        """)
        lugares = cursor.fetchall()
        informacion["lugares"] = [
            {
                "nombre": lugar[0],
                "descripcion": lugar[1] if lugar[1] else "",
                "calificacion": float(lugar[2]) if lugar[2] else None
            }
            for lugar in lugares
        ]
        
        cursor.close()
        connection.close()
        return jsonify(informacion)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/panel')
def panel():
    try:
        connection = get_db_connection()
        if not connection:
            return render_template("panel_admin.html", ciudades=[], categorias=[], lugares=[], error="No se pudo conectar a la base de datos")

        cursor = connection.cursor()

        # Obtener ciudades
        cursor.execute("SELECT id_ciudad, nombre FROM ciudades")
        ciudades = cursor.fetchall()

        # Obtener categorías
        cursor.execute("SELECT id_categoria, nombre FROM categorias")
        categorias = cursor.fetchall()

        # Obtener lugares
        cursor.execute("""
            SELECT 
                l.id_lugar,
                l.nombre,
                IFNULL(c.nombre, 'Sin ciudad') AS ciudad,
                IFNULL(cat.nombre, 'Sin categoría') AS categoria,
                l.calificacion
            FROM lugares l
            LEFT JOIN ciudades c ON l.id_ciudad = c.id_ciudad
            LEFT JOIN categorias cat ON l.id_categoria = cat.id_categoria
            ORDER BY l.id_lugar DESC
        """)

        lugares = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template(
            "panel_admin.html",
            ciudades=ciudades,
            categorias=categorias,
            lugares=lugares
        )
    except Exception as e:
        return render_template("panel_admin.html", ciudades=[], categorias=[], lugares=[], error=str(e))

@app.route('/lugares', methods=['GET'])
def obtener_lugares():
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM lugares")
        datos = cursor.fetchall()
        
        lugares = []
        for fila in datos:
            lugares.append({
                "id": fila[0],
                "nombre": fila[1],
                "descripcion": fila[2],
                "direccion": fila[3],
                "latitud": float(fila[4]) if fila[4] else None,
                "longitud": float(fila[5]) if fila[5] else None,
                "id_ciudad": fila[6],
                "id_categoria": fila[7],
                "calificacion": float(fila[8]) if fila[8] else None,
                "precio_promedio": float(fila[9]) if fila[9] else None
            })
        
        cursor.close()
        connection.close()
        return jsonify(lugares)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Buscar lugares por radio
# -------------------------------
# -------------------------------
# Eliminar un lugar
# -------------------------------
@app.route('/eliminar_lugar/<int:id_lugar>', methods=['DELETE', 'POST'])
def eliminar_lugar(id_lugar):
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

        cursor = connection.cursor()
        cursor.execute("DELETE FROM lugares WHERE id_lugar = %s", (id_lugar,))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"mensaje": "Lugar eliminado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Obtener un lugar específico
# -------------------------------
@app.route('/obtener_lugar/<int:id_lugar>', methods=['GET'])
def obtener_lugar(id_lugar):
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

        cursor = connection.cursor()
        cursor.execute("""
            SELECT 
                l.id_lugar,
                l.nombre,
                l.descripcion,
                l.direccion,
                l.latitud,
                l.longitud,
                l.id_ciudad,
                l.id_categoria,
                l.calificacion,
                l.precio_promedio
            FROM lugares l
            WHERE l.id_lugar = %s
        """, (id_lugar,))
        
        lugar = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if lugar:
            return jsonify({
                "id_lugar": lugar[0],
                "nombre": lugar[1],
                "descripcion": lugar[2],
                "direccion": lugar[3],
                "latitud": float(lugar[4]) if lugar[4] else None,
                "longitud": float(lugar[5]) if lugar[5] else None,
                "id_ciudad": lugar[6],
                "id_categoria": lugar[7],
                "calificacion": float(lugar[8]) if lugar[8] else None,
                "precio_promedio": float(lugar[9]) if lugar[9] else None
            })
        return jsonify({"error": "Lugar no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# Actualizar un lugar
# -------------------------------
@app.route('/actualizar_lugar/<int:id_lugar>', methods=['POST'])
def actualizar_lugar(id_lugar):
    try:
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        direccion = request.form.get('direccion')
        latitud = request.form.get('latitud')
        longitud = request.form.get('longitud')
        id_ciudad = request.form.get('id_ciudad')
        id_categoria = request.form.get('id_categoria')
        
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

        cursor = connection.cursor()
        query = """
        UPDATE lugares
        SET nombre=%s, descripcion=%s, direccion=%s, latitud=%s, 
            longitud=%s, id_ciudad=%s, id_categoria=%s
        WHERE id_lugar=%s
        """
        
        cursor.execute(query, (nombre, descripcion, direccion, latitud, 
                              longitud, id_ciudad, id_categoria, id_lugar))
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({"mensaje": "Lugar actualizado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/lugares/cercanos', methods=['GET'])
def lugares_cercanos():
    try:
        lat = request.args.get('lat')
        lng = request.args.get('lng')
        radio = request.args.get('radio', 2)

        if not lat or not lng:
            return jsonify({"error": "Debes enviar lat y lng"}), 400

        lat = float(lat)
        lng = float(lng)
        radio = float(radio)

        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

        cursor = connection.cursor()

        query = """
        SELECT *, 
        ( 6371 * acos(
            cos(radians(%s)) *
            cos(radians(latitud)) *
            cos(radians(longitud) - radians(%s)) +
            sin(radians(%s)) *
            sin(radians(latitud))
        )) AS distancia
        FROM lugares
        HAVING distancia < %s
        ORDER BY distancia
        """

        cursor.execute(query, (lat, lng, lat, radio))
        datos = cursor.fetchall()

        resultados = []
        for fila in datos:
            resultados.append({
                "id": fila[0],
                "nombre": fila[1],
                "distancia_km": round(fila[-1], 2)
            })

        cursor.close()
        connection.close()

        return jsonify(resultados)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)