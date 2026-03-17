from flask import Flask, request, jsonify, render_template
import pymysql
pymysql.install_as_MySQLdb()
from flask_mysqldb import MySQL
from flask_cors import CORS
import math
import os

app = Flask(__name__)
CORS(app)

# Configuración MySQL
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'interchange.proxy.rlwy.net')
app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT', 14605))
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'ZqSbhxOGMnxsXrhoXYTLftiBWtbFWutt')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'railway')
mysql = MySQL(app)

# -------------------------------
# Obtener todos los lugares
# -------------------------------

@app.route('/', methods=['GET'])
def inicio():
    return render_template('agregar_lugar.html')

from flask import render_template

@app.route('/obtener_ciudades', methods=['GET'])
def obtener_ciudades():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id_ciudad, nombre FROM ciudades")
    ciudades = cursor.fetchall()
    cursor.close()
    return jsonify(list(ciudades))

@app.route('/obtener_categorias', methods=['GET'])
def obtener_categorias():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id_categoria, nombre FROM categorias")
    categorias = cursor.fetchall()
    cursor.close()
    return jsonify(list(categorias))

@app.route('/guardar_lugar', methods=['POST'])
def guardar_lugar():
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion', '')
    direccion = request.form.get('direccion', '')
    latitud = request.form.get('latitud')
    longitud = request.form.get('longitud')
    id_ciudad = request.form.get('id_ciudad')
    id_categoria = request.form.get('id_categoria')

    try:
        cursor = mysql.connection.cursor()
        query = """
        INSERT INTO lugares
        (nombre, descripcion, direccion, latitud, longitud, id_ciudad, id_categoria)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(query, (nombre, descripcion, direccion, latitud, longitud, id_ciudad, id_categoria))
        mysql.connection.commit()
        cursor.close()
        return "Lugar agregado correctamente", 200
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/lugares', methods=['GET'])
def api_lugares():
    cursor = mysql.connection.cursor()
    
    try:
        # Obtener lugares con información completa incluyendo estado y país de ciudades
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
        
        # Formatear los datos (sin incluir ids)
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
        return jsonify(lugares_json)
        
    except Exception as e:
        cursor.close()
        return jsonify({"error": str(e)}), 500

@app.route('/extraer_informacion', methods=['GET'])
def extraer_informacion():
    cursor = mysql.connection.cursor()
    
    try:
        # Extraer información de las 3 tablas (5 campos en total)
        informacion = {
            "ciudades": [],
            "categorias": [],
            "lugares": []
        }
        
        # 1 campo de ciudades: nombre
        cursor.execute("SELECT nombre FROM ciudades ORDER BY nombre")
        ciudades = cursor.fetchall()
        informacion["ciudades"] = [ciudad[0] for ciudad in ciudades]
        
        # 1 campo de categorias: nombre
        cursor.execute("SELECT nombre FROM categorias ORDER BY nombre")
        categorias = cursor.fetchall()
        informacion["categorias"] = [categoria[0] for categoria in categorias]
        
        # 3 campos de lugares: nombre, descripcion, calificacion
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
        return jsonify(informacion)
        
    except Exception as e:
        cursor.close()
        return jsonify({"error": str(e)}), 500

@app.route('/panel')
def panel():

    cursor = mysql.connection.cursor()

    # Obtener ciudades
    cursor.execute("SELECT id_ciudad, nombre FROM ciudades")
    ciudades = cursor.fetchall()

    # Obtener categorias
    cursor.execute("SELECT id_categoria, nombre FROM categorias")
    categorias = cursor.fetchall()

    # Obtener lugares con LEFT JOIN para ver incluso los que no tienen relaciones
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

    return render_template(
        "panel_admin.html",
        ciudades=ciudades,
        categorias=categorias,
        lugares=lugares
    )

@app.route('/lugares', methods=['GET'])
def obtener_lugares():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM lugares")
    datos = cursor.fetchall()
    
    lugares = []
    for fila in datos:
        lugares.append({
            "id": fila[0],
            "nombre": fila[1],
            "descripcion": fila[2],
            "direccion": fila[3],
            "latitud": fila[4],
            "longitud": fila[5],
            "id_ciudad": fila[6],
            "id_categoria": fila[7],
            "calificacion": float(fila[8]) if fila[8] else None,
            "precio_promedio": float(fila[9]) if fila[9] else None
        })
    
    return jsonify(lugares)

# -------------------------------
# Buscar lugares por radio
# -------------------------------
# -------------------------------
# Eliminar un lugar
# -------------------------------
@app.route('/eliminar_lugar/<int:id_lugar>', methods=['DELETE', 'POST'])
def eliminar_lugar(id_lugar):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM lugares WHERE id_lugar = %s", (id_lugar,))
    mysql.connection.commit()
    return jsonify({"mensaje": "Lugar eliminado correctamente"})

# -------------------------------
# Obtener un lugar específico
# -------------------------------
@app.route('/obtener_lugar/<int:id_lugar>', methods=['GET'])
def obtener_lugar(id_lugar):
    cursor = mysql.connection.cursor()
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
    
    if lugar:
        return jsonify({
            "id_lugar": lugar[0],
            "nombre": lugar[1],
            "descripcion": lugar[2],
            "direccion": lugar[3],
            "latitud": lugar[4],
            "longitud": lugar[5],
            "id_ciudad": lugar[6],
            "id_categoria": lugar[7],
            "calificacion": lugar[8],
            "precio_promedio": lugar[9]
        })
    return jsonify({"error": "Lugar no encontrado"}), 404

# -------------------------------
# Actualizar un lugar
# -------------------------------
@app.route('/actualizar_lugar/<int:id_lugar>', methods=['POST'])
def actualizar_lugar(id_lugar):
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')
    direccion = request.form.get('direccion')
    latitud = request.form.get('latitud')
    longitud = request.form.get('longitud')
    id_ciudad = request.form.get('id_ciudad')
    id_categoria = request.form.get('id_categoria')
    
    cursor = mysql.connection.cursor()
    
    query = """
    UPDATE lugares
    SET nombre=%s, descripcion=%s, direccion=%s, latitud=%s, 
        longitud=%s, id_ciudad=%s, id_categoria=%s
    WHERE id_lugar=%s
    """
    
    cursor.execute(query, (nombre, descripcion, direccion, latitud, 
                          longitud, id_ciudad, id_categoria, id_lugar))
    mysql.connection.commit()
    
    return jsonify({"mensaje": "Lugar actualizado correctamente"})

@app.route('/lugares/cercanos', methods=['GET'])
def lugares_cercanos():
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    radio = request.args.get('radio', 2)

    if not lat or not lng:
        return jsonify({"error": "Debes enviar lat y lng"}), 400

    lat = float(lat)
    lng = float(lng)
    radio = float(radio)

    cursor = mysql.connection.cursor()

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
    ORDER BY distancia;
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

    return jsonify(resultados)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)