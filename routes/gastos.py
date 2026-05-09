from flask import Blueprint, jsonify, redirect, request, render_template
from database import get_connection


gastos_bp = Blueprint('gastos', __name__)

def procesar_gasto(monto, categoria, fecha, notas=None):

    TIPOS_ALERTA = {
        "presupuesto_excedido": 1,
        "umbral_presupuesto": 2,
        "gasto_atipico": 3
    }

    alertas_generadas = []

    conexion = get_connection()
    cursor = conexion.cursor()

    try:

        # Calcular promedio histórico ANTES del nuevo gasto
        cursor.execute("""
        SELECT AVG(monto)
        FROM gastos
        WHERE id_usuario = %s
        AND id_categoria = %s
        AND activo = TRUE
        """, (1, categoria))

        promedio = cursor.fetchone()[0]

        # Insertar gasto
        query = """
        INSERT INTO gastos (id_usuario, id_categoria, monto, fecha, notas)
        VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(query, (1, categoria, monto, fecha, notas))

        id_gasto = cursor.lastrowid

        # Registrar historial
        query_historial = """
        INSERT INTO gastos_historial
        (id_gasto, accion, monto, id_usuario_accion, descripcion_cambio)
        VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(
            query_historial,
            (id_gasto, 'INSERT', monto, 1, 'Gasto registrado')
        )

        # Calcular gasto total
        cursor.execute("""
        SELECT SUM(monto)
        FROM gastos
        WHERE id_usuario = %s
        AND id_categoria = %s
        AND activo = TRUE
        """, (1, categoria))

        total_gastado = cursor.fetchone()[0] or 0

        # Obtener límite de presupuesto
        cursor.execute("""
        SELECT monto_limite
        FROM presupuestos
        WHERE id_usuario = %s
        AND id_categoria = %s
        """, (1, categoria))

        resultado = cursor.fetchone()
        limite = resultado[0] if resultado else None

        if limite is not None:

            porcentaje = (total_gastado / limite) * 100

            if total_gastado > limite:

                mensaje = (
                    f"Has excedido tu presupuesto. "
                    f"Total: {total_gastado}, Límite: {limite}"
                )

                cursor.execute("""
                INSERT INTO alertas (id_usuario, id_tipo_alerta, mensaje)
                VALUES (%s, %s, %s)
                """, (1, TIPOS_ALERTA["presupuesto_excedido"], mensaje))

                alertas_generadas.append(mensaje)

            elif porcentaje >= 80:

                mensaje = (
                    f"Advertencia: llevas "
                    f"{porcentaje:.2f}% de tu presupuesto"
                )

                cursor.execute("""
                INSERT INTO alertas (id_usuario, id_tipo_alerta, mensaje)
                VALUES (%s, %s, %s)
                """, (1, TIPOS_ALERTA["umbral_presupuesto"], mensaje))

                alertas_generadas.append(mensaje)

        # Detectar gasto atípico
        if promedio and monto > (promedio * 2):

            mensaje = (
                f"Gasto inusual detectado. "
                f"Monto: {monto}, Promedio: {promedio:.2f}"
            )

            cursor.execute("""
            INSERT INTO alertas (id_usuario, id_tipo_alerta, mensaje)
            VALUES (%s, %s, %s)
            """, (1, TIPOS_ALERTA["gasto_atipico"], mensaje))

            alertas_generadas.append(mensaje)

        conexion.commit()

        return {
            "mensaje": "Gasto guardado con historial",
            "alertas": alertas_generadas
        }

    finally:
        cursor.close()
        conexion.close()

@gastos_bp.route('/gastos', methods=['GET'])
def obtener_gastos():
    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM gastos WHERE activo = TRUE"
        )

        gastos = cursor.fetchall()

        return jsonify(gastos)

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cursor.close()
        conexion.close()


@gastos_bp.route('/gastos', methods=['POST'])
def crear_gasto():

    data = request.json

    resultado = procesar_gasto(
        float(data.get('monto')),
        data.get('categoria'),
        data.get('fecha'),
        data.get('notas')
    )

    return jsonify(resultado)


@gastos_bp.route('/gastos/<int:id_gasto>', methods=['PUT'])
def actualizar_gasto(id_gasto):
    data = request.json

    monto = data.get('monto')
    categoria = data.get('categoria')
    fecha = data.get('fecha')

    try:
        conexion = get_connection()
        cursor = conexion.cursor()

        # 🔥 VALIDAR EXISTENCIA DEL ID_GASTO A ACTUALIZAR 
        cursor.execute("SELECT id_gasto FROM gastos WHERE id_gasto = %s", (id_gasto,))
        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({"error": "Gasto no existe"}), 404

        # 🔥 ACTUALIZAR GASTO
        query_update = """
        UPDATE gastos
        SET monto = %s, id_categoria = %s, fecha = %s
        WHERE id_gasto = %s
        """

        cursor.execute(query_update, (monto, categoria, fecha, id_gasto))

        # 🔥 GUARDAR HISTORIAL
        query_historial = """
        INSERT INTO gastos_historial (id_gasto, accion, monto, id_usuario_accion, descripcion_cambio)
        VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(query_historial, (id_gasto, 'UPDATE', monto, 1, 'Gasto actualizado'))

        conexion.commit()

        return jsonify({
            "mensaje": "Gasto actualizado correctamente"
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        })

    finally:
        cursor.close()
        conexion.close()

@gastos_bp.route('/gastos/<int:id_gasto>', methods=['DELETE'])
def eliminar_gasto(id_gasto):
    try:
        conexion = get_connection()
        cursor = conexion.cursor()

        # 🔥 Validar existencia + obtener datos
        cursor.execute(
            "SELECT monto FROM gastos WHERE id_gasto = %s AND activo = TRUE",
            (id_gasto,)
        )
        resultado = cursor.fetchone()

        if not resultado:
            return jsonify({"error": "Gasto no existe o ya fue eliminado"}), 404

        monto = resultado[0]

        # 🔥 SOFT DELETE
        cursor.execute(
            """
            UPDATE gastos
            SET activo = FALSE, deleted_at = NOW()
            WHERE id_gasto = %s
            """,
            (id_gasto,)
        )

        # 🔥 Guardar historial
        query_historial = """
        INSERT INTO gastos_historial (id_gasto, accion, monto, id_usuario_accion, descripcion_cambio)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query_historial, (id_gasto, 'DELETE', monto, 1, 'Gasto eliminado'))

        conexion.commit()

        return jsonify({
            "mensaje": "Gasto eliminado (soft delete) correctamente"
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        })

    finally:
        cursor.close()
        conexion.close()

@gastos_bp.route('/alertas', methods=['GET'])
def obtener_alertas():
    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                a.id_alerta,
                t.nombre AS tipo_alerta,
                a.mensaje,
                a.fecha
            FROM alertas a
            JOIN tipos_alerta t 
                ON a.id_tipo_alerta = t.id_tipo_alerta
            WHERE a.id_usuario = %s
            ORDER BY a.fecha DESC
        """, (1,))

        alertas = cursor.fetchall()

        return jsonify(alertas)

    except Exception as e:
        return jsonify({
            "error": str(e)
        })

    finally:
        cursor.close()
        conexion.close()

@gastos_bp.route('/api/historial', methods=['GET'])
def obtener_historial():
    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                gh.id_historial,
                gh.id_gasto,
                gh.accion,
                gh.monto,
                gh.fecha,
                u.nombre AS usuario_accion
            FROM gastos_historial gh
            JOIN usuarios u
                ON gh.id_usuario_accion = u.id_usuario
            ORDER BY gh.fecha DESC
        """)

        historial = cursor.fetchall()

        return jsonify(historial)

    except Exception as e:
        return jsonify({
            "error": str(e)
        })

    finally:
        cursor.close()
        conexion.close()

@gastos_bp.route('/dashboard', methods=['GET'])
def dashboard():
    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        # TOTAL GASTADO
        cursor.execute("""
            SELECT SUM(monto) AS total_gastado
            FROM gastos
            WHERE id_usuario = %s
            AND activo = TRUE
        """, (1,))
        total = cursor.fetchone()

        # TOTAL MOVIMIENTOS
        cursor.execute("""
            SELECT COUNT(*) AS total_gastos
            FROM gastos
            WHERE id_usuario = %s
            AND activo = TRUE
        """, (1,))
        cantidad = cursor.fetchone()

        # PROMEDIO
        cursor.execute("""
            SELECT AVG(monto) AS promedio
            FROM gastos
            WHERE id_usuario = %s
            AND activo = TRUE
        """, (1,))
        promedio = cursor.fetchone()

        # ALERTAS
        cursor.execute("""
            SELECT COUNT(*) AS total_alertas
            FROM alertas
            WHERE id_usuario = %s
        """, (1,))
        alertas = cursor.fetchone()

        # CATEGORÍA CON MÁS GASTO
        cursor.execute("""
            SELECT 
                c.nombre_categoria,
                SUM(g.monto) AS total_categoria
            FROM gastos g
            JOIN categorias c
                ON g.id_categoria = c.id_categoria
            WHERE g.id_usuario = %s
            AND g.activo = TRUE
            GROUP BY c.nombre_categoria
            ORDER BY total_categoria DESC
            LIMIT 1
        """, (1,))
        categoria_top = cursor.fetchone()

        return jsonify({
            "total_gastado": total["total_gastado"] or 0,
            "total_gastos": cantidad["total_gastos"],
            "promedio_gasto": promedio["promedio"] or 0,
            "total_alertas": alertas["total_alertas"],
            "categoria_top": categoria_top
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        })

    finally:
        cursor.close()
        conexion.close()

@gastos_bp.route('/dashboard-view', methods=['GET'])
def dashboard_view():

    filtro = request.args.get('filtro', '30')

    condicion_fecha = ""

    if filtro == '1':
        condicion_fecha = "AND fecha >= NOW() - INTERVAL 1 DAY"
    elif filtro == '7':
        condicion_fecha = "AND fecha >= NOW() - INTERVAL 7 DAY"
    elif filtro == '30':
        condicion_fecha = "AND fecha >= NOW() - INTERVAL 30 DAY"

    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(f"""
            SELECT SUM(monto) AS total_gastado
            FROM gastos
            WHERE id_usuario = %s
            AND activo = TRUE
            {condicion_fecha}
        """, (1,))
        total = cursor.fetchone()

        cursor.execute(f"""
            SELECT COUNT(*) AS total_gastos
            FROM gastos
            WHERE id_usuario = %s
            AND activo = TRUE
            {condicion_fecha}
        """, (1,))
        cantidad = cursor.fetchone()

        cursor.execute(f""" 
            SELECT AVG(monto) AS promedio 
            FROM gastos
            WHERE id_usuario = %s AND activo = TRUE {condicion_fecha}
        """, (1,)) 
        promedio = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) AS total_alertas
            FROM alertas
            WHERE id_usuario = %s
        """, (1,))
        alertas = cursor.fetchone()

        cursor.execute(f"""
            SELECT 
                c.nombre_categoria,
                SUM(g.monto) AS total_categoria
            FROM gastos g
            JOIN categorias c
                ON g.id_categoria = c.id_categoria
            WHERE g.id_usuario = %s
            AND g.activo = TRUE
            {condicion_fecha}
            GROUP BY c.nombre_categoria
            ORDER BY total_categoria DESC
            LIMIT 1
        """, (1,))
        categoria_top = cursor.fetchone()

        cursor.execute("""
            SELECT mensaje, fecha
            FROM alertas
            WHERE id_usuario = %s
            ORDER BY fecha DESC
            LIMIT 5
        """, (1,))
        alertas_recientes = cursor.fetchall()

        cursor.execute(f"""
            SELECT 
                c.nombre_categoria,
                SUM(g.monto) AS total
            FROM gastos g
            JOIN categorias c
                ON g.id_categoria = c.id_categoria
            WHERE g.id_usuario = %s
            AND g.activo = TRUE
            {condicion_fecha}
            GROUP BY c.nombre_categoria
        """, (1,))

        categorias_grafica = cursor.fetchall()

        categorias = [item['nombre_categoria'] for item in categorias_grafica]
        montos = [item['total'] for item in categorias_grafica]

        return render_template(
            'dashboard.html',
            total_gastado=total["total_gastado"] or 0,
            total_gastos=cantidad["total_gastos"],
            promedio_gasto=promedio["promedio"] or 0,            
            total_alertas=alertas["total_alertas"],
            categoria_top=categoria_top,
            alertas_recientes=alertas_recientes,
            filtro=filtro,
            categorias_grafica=categorias_grafica,
            categorias=categorias,
            montos=montos
        )

    except Exception as e:
        return str(e)

    finally:
        cursor.close()
        conexion.close()

@gastos_bp.route('/registrar-gasto', methods=['GET', 'POST'])
def registrar_gasto():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id_categoria, nombre_categoria FROM categorias")
    categorias = cursor.fetchall()

    if request.method == 'GET':
        cursor.close()
        conn.close()

        return render_template(
            'registrar_gasto.html',
            categorias=categorias
        )

    data = request.form

    resultado = procesar_gasto(
        float(data.get('monto')),
        data.get('categoria'),
        data.get('fecha'),
        data.get('notas')
    )

    cursor.close()
    conn.close()

    return render_template(
        'registrar_gasto.html',
        categorias=categorias,
        mensaje=resultado["mensaje"],
        alertas=resultado["alertas"]
    )


@gastos_bp.route('/historial', methods=['GET'])
def ver_historial():

    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                gh.id_historial,
                gh.id_gasto,
                gh.accion,
                gh.descripcion_cambio,
                gh.monto,
                gh.fecha,
                u.nombre AS usuario_accion
            FROM gastos_historial gh
            JOIN usuarios u
                ON gh.id_usuario_accion = u.id_usuario
            ORDER BY gh.fecha DESC
        """)

        historial = cursor.fetchall()

        return render_template(
            'historial.html',
            historial=historial
        )

    except Exception as e:
        return str(e)

    finally:
        cursor.close()
        conexion.close()
        
@gastos_bp.route('/editar-gasto/<int:id_gasto>', methods=['GET', 'POST'])
def editar_gasto(id_gasto):

    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        if request.method == 'GET':

            cursor.execute("""
                SELECT *
                FROM gastos
                WHERE id_gasto = %s
                AND activo = TRUE
            """, (id_gasto,))

            gasto = cursor.fetchone()

            cursor.execute("""
                SELECT id_categoria, nombre_categoria
                FROM categorias
            """)

            categorias = cursor.fetchall()

            return render_template(
                'editar_gasto.html',
                gasto=gasto,
                categorias=categorias
            )

        data = request.form

        monto = float(data.get('monto'))
        categoria = int(data.get('categoria'))
        fecha = data.get('fecha')
        notas = data.get('notas')

        # Obtener valores actuales
        cursor.execute("""
            SELECT monto, id_categoria, fecha, notas
            FROM gastos
            WHERE id_gasto = %s
        """, (id_gasto,))

        gasto_actual = cursor.fetchone()

        cambios = []

        if float(gasto_actual['monto']) != monto:
            cambios.append(f"Monto: {gasto_actual['monto']} → {monto}")

        if gasto_actual['id_categoria'] != categoria:

            cursor.execute("""
                SELECT nombre_categoria
                FROM categorias
                WHERE id_categoria = %s
            """, (gasto_actual['id_categoria'],))

            categoria_anterior = cursor.fetchone()['nombre_categoria']

            cursor.execute("""
                SELECT nombre_categoria
                FROM categorias
                WHERE id_categoria = %s
            """, (categoria,))

            categoria_nueva = cursor.fetchone()['nombre_categoria']

            cambios.append(
                f"Categoría: {categoria_anterior} → {categoria_nueva}"
            )

        fecha_actual = gasto_actual['fecha'].strftime('%Y-%m-%dT%H:%M')

        if fecha_actual != fecha:
            cambios.append("Fecha modificada")

        if (gasto_actual['notas'] or '') != (notas or ''):
            cambios.append("Notas modificadas")

        descripcion_cambio = " | ".join(cambios)

        cursor.execute("""
            UPDATE gastos
            SET monto = %s,
                id_categoria = %s,
                fecha = %s,
                notas = %s
            WHERE id_gasto = %s
        """, (monto, categoria, fecha, notas, id_gasto))

        cursor.execute("""
            INSERT INTO gastos_historial
            (id_gasto, accion, monto, id_usuario_accion, descripcion_cambio)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_gasto, 'UPDATE', monto, 1, descripcion_cambio))

        conexion.commit()

        return redirect('/historial')

    except Exception as e:
        return str(e)

    finally:
        cursor.close()
        conexion.close()

@gastos_bp.route('/eliminar-gasto/<int:id_gasto>')
def eliminar_gasto_view(id_gasto):

    try:
        conexion = get_connection()
        cursor = conexion.cursor()

        # Obtener monto actual
        cursor.execute("""
            SELECT monto
            FROM gastos
            WHERE id_gasto = %s
        """, (id_gasto,))

        resultado = cursor.fetchone()

        if not resultado:
            return "Gasto no encontrado"

        monto_actual = resultado[0]

        # Soft delete
        cursor.execute("""
            UPDATE gastos
            SET activo = FALSE,
                deleted_at = NOW()
            WHERE id_gasto = %s
        """, (id_gasto,))

        # Registrar historial con monto real
        cursor.execute("""
        INSERT INTO gastos_historial
        (id_gasto, accion, monto, id_usuario_accion, descripcion_cambio)
        VALUES (%s, %s, %s, %s, %s)
        """, (id_gasto, 'DELETE', monto_actual, 1, 'Gasto eliminado'))

        conexion.commit()

        return redirect('/historial')

    except Exception as e:
        return str(e)

    finally:
        cursor.close()
        conexion.close()

@gastos_bp.route('/gastos-view', methods=['GET'])
def ver_gastos():

    try:
        conexion = get_connection()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                g.id_gasto,
                c.nombre_categoria,
                g.monto,
                g.fecha,
                g.notas
            FROM gastos g
            JOIN categorias c
                ON g.id_categoria = c.id_categoria
            WHERE g.id_usuario = %s
            AND g.activo = TRUE
            ORDER BY g.fecha DESC
        """, (1,))

        gastos = cursor.fetchall()

        return render_template(
            'gastos.html',
            gastos=gastos
        )

    except Exception as e:
        return str(e)

    finally:
        cursor.close()
        conexion.close()