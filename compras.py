from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, current_app
from sqlalchemy import or_

compras_bp = Blueprint('compras', __name__, template_folder='templates')


def _get_db_y_session():
    ext = current_app.extensions.get('sqlalchemy')
    db_inst = getattr(ext, 'db', ext)
    return db_inst, db_inst.session


def _obtener_stock_total_seguro(producto):
    try:
        from app import obtener_stock_total
        val = obtener_stock_total(producto)
        if val is not None:
            return float(val)
    except Exception:
        pass

    if hasattr(producto, 'stocks') and producto.stocks is not None:
        if isinstance(producto.stocks, (list, tuple)) or hasattr(producto.stocks, '__iter__'):
            return sum(float(getattr(s, 'cantidad', getattr(s, 'stock', 0)) or 0) for s in producto.stocks)
        return float(producto.stocks or 0)
    if hasattr(producto, 'stock'):
        return float(producto.stock or 0)
    return 0.0


def aumentar_stock(producto, cantidad):
    """Suma la cantidad al stock del producto reconociendo la estructura del modelo."""
    if hasattr(producto, 'stocks'):
        if isinstance(producto.stocks, (list, tuple)) or hasattr(producto.stocks, '__iter__'):
            if len(producto.stocks) > 0:
                s = producto.stocks[0]
                if hasattr(s, 'cantidad'):
                    s.cantidad = (s.cantidad or 0) + cantidad
                elif hasattr(s, 'stock'):
                    s.stock = (s.stock or 0) + cantidad
        else:
            producto.stocks = (producto.stocks or 0) + cantidad
    elif hasattr(producto, 'stock'):
        producto.stock = (producto.stock or 0) + cantidad


def restar_stock(producto, cantidad):
    """Resta la cantidad al stock del producto al revertir o eliminar una compra."""
    if hasattr(producto, 'stocks'):
        if isinstance(producto.stocks, (list, tuple)) or hasattr(producto.stocks, '__iter__'):
            if len(producto.stocks) > 0:
                s = producto.stocks[0]
                if hasattr(s, 'cantidad'):
                    s.cantidad = max(0, (s.cantidad or 0) - cantidad)
                elif hasattr(s, 'stock'):
                    s.stock = max(0, (s.stock or 0) - cantidad)
        else:
            producto.stocks = max(0, (producto.stocks or 0) - cantidad)
    elif hasattr(producto, 'stock'):
        producto.stock = max(0, (producto.stock or 0) - cantidad)


def _recalcular_estado_compra(compra):
    items = compra.items or []
    if not items:
        compra.estado = 'PLANIFICADA'
        compra.total_confirmado = 0.0
        return

    confirmados = [i for i in items if (getattr(i, 'estado', None) or 'PENDIENTE').upper() == 'CONFIRMADO']
    pendientes = [i for i in items if (getattr(i, 'estado', None) or 'PENDIENTE').upper() == 'PENDIENTE']

    compra.total_confirmado = sum(float(i.subtotal or 0.0) for i in confirmados)

    if len(confirmados) == 0:
        compra.estado = 'PLANIFICADA'
    elif len(pendientes) > 0:
        compra.estado = 'PARCIAL'
    else:
        compra.estado = 'COMPLETADA'


def _aplicar_confirmacion_item_en_inventario(item, sess, Producto):
    nombre_prod = (item.nombre or '').strip()
    cant = float(item.cantidad or 0.0)
    precio_u = float(item.precio or 0.0)

    if not nombre_prod or cant <= 0:
        raise ValueError("Cantidad o nombre de producto inválido para confirmar.")

    prod = sess.query(Producto).filter(Producto.nombre.ilike(nombre_prod)).first()
    if not prod:
        raise ValueError(f"El producto '{nombre_prod}' no existe en el inventario.")

    stock_actual = _obtener_stock_total_seguro(prod)
    costo_actual = float(prod.precio_costo or 0.0)

    if stock_actual > 0 and costo_actual > 0:
        valor_inventario_existente = stock_actual * costo_actual
        valor_nueva_compra = cant * precio_u
        nuevo_stock_total = stock_actual + cant
        costo_ponderado = (valor_inventario_existente + valor_nueva_compra) / nuevo_stock_total
        prod.precio_costo = round(costo_ponderado, 2)
    else:
        prod.precio_costo = precio_u

    aumentar_stock(prod, cant)


def _obtener_saldos_socios_actuales(sess):
    from app import Propietario, calcular_saldos_propietario
    propietarios = sess.query(Propietario).all()
    saldos = {}
    for prop in propietarios:
        datos = calcular_saldos_propietario(prop, session_db=sess)
        saldos[str(prop.id)] = {
            'efectivo': datos['efectivo'],
            'transferencia': datos['transferencia']
        }
    return saldos


@compras_bp.route('/compras', methods=['GET'])
def vista_compras():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    from app import Proveedor, Propietario, Producto, calcular_saldos_propietario

    _, sess = _get_db_y_session()

    proveedores = sess.query(Proveedor).all()
    propietarios = sess.query(Propietario).all()
    productos = sess.query(Producto).filter(or_(Producto.activo == True, Producto.activo.is_(None))).all()

    saldos_socios = {}
    for prop in propietarios:
        datos_saldo = calcular_saldos_propietario(prop, session_db=sess)
        saldos_socios[str(prop.id)] = {
            'efectivo': datos_saldo['efectivo'],
            'transferencia': datos_saldo['transferencia']
        }

    return render_template(
        'compras.html',
        proveedores=proveedores,
        propietarios=propietarios,
        productos=productos,
        saldos_socios=saldos_socios
    )


@compras_bp.route('/api/guardar_compra', methods=['POST'])
def guardar_compra():
    from app import Compra, ItemCompra
    datos = request.get_json(silent=True) or {}

    efectivo_inicial = float(datos.get('efectivo_inicial', 0))
    propietario_id = datos.get('propietario_id')
    metodo_pago = datos.get('metodo_pago', 'EFECTIVO')
    items_compra = datos.get('items', [])

    if not items_compra:
        return jsonify({"success": False, "mensaje": "La lista de compra está vacía."}), 400

    if not propietario_id:
        return jsonify({"success": False, "mensaje": "Debes seleccionar el socio comprador."}), 400

    total_compra = sum(float(item['subtotal']) for item in items_compra)
    efectivo_restante = efectivo_inicial - total_compra

    _, sess = _get_db_y_session()

    try:
        nueva_compra = Compra(
            propietario_id=int(propietario_id),
            metodo_pago=metodo_pago,
            efectivo_inicial=efectivo_inicial,
            total_compra=total_compra,
            total_confirmado=0.0,
            efectivo_restante=efectivo_restante,
            estado='PLANIFICADA'
        )
        sess.add(nueva_compra)
        sess.flush()

        for item in items_compra:
            nombre_prod = item['nombre'].strip()
            cant = float(item['cantidad'])
            precio_u = float(item['precio'])

            nuevo_item = ItemCompra(
                compra_id=nueva_compra.id,
                nombre=nombre_prod,
                proveedor=item['proveedor'],
                cantidad=cant,
                precio=precio_u,
                subtotal=float(item['subtotal']),
                estado='PENDIENTE'
            )
            sess.add(nuevo_item)

        sess.commit()

        return jsonify({
            "success": True,
            "mensaje": "¡Compra planificada guardada! Confirma cada producto cuando regreses."
        })
    except Exception as e:
        sess.rollback()
        return jsonify({"success": False, "mensaje": f"Error al guardar: {str(e)}"}), 500


@compras_bp.route('/api/compras/items/<int:item_id>/editar', methods=['POST'])
def editar_item_compra(item_id):
    from app import ItemCompra
    datos = request.get_json(silent=True) or {}
    _, sess = _get_db_y_session()

    try:
        item = sess.get(ItemCompra, item_id)
        if not item:
            return jsonify({"success": False, "mensaje": "Ítem de compra no encontrado."}), 404

        if (getattr(item, 'estado', None) or 'PENDIENTE').upper() == 'CONFIRMADO':
            return jsonify({"success": False, "mensaje": "No puedes editar un producto ya confirmado."}), 400

        cant = float(datos.get('cantidad', item.cantidad))
        precio_u = float(datos.get('precio', item.precio))
        if cant <= 0 or precio_u < 0:
            return jsonify({"success": False, "mensaje": "Cantidad o precio inválido."}), 400

        item.cantidad = cant
        item.precio = precio_u
        item.subtotal = cant * precio_u

        compra = item.compra
        compra.total_compra = sum(
            float(i.subtotal or 0.0)
            for i in (compra.items or [])
            if (getattr(i, 'estado', None) or 'PENDIENTE').upper() != 'NO_COMPRADO'
        )
        _recalcular_estado_compra(compra)
        sess.commit()

        return jsonify({"success": True, "mensaje": "Producto actualizado en la compra."})
    except Exception as e:
        sess.rollback()
        return jsonify({"success": False, "mensaje": f"Error al editar: {str(e)}"}), 500


@compras_bp.route('/api/compras/items/<int:item_id>/confirmar', methods=['POST'])
def confirmar_item_compra(item_id):
    from app import ItemCompra, Producto
    datos = request.get_json(silent=True) or {}
    _, sess = _get_db_y_session()

    try:
        item = sess.get(ItemCompra, item_id)
        if not item:
            return jsonify({"success": False, "mensaje": "Ítem de compra no encontrado."}), 404

        if (getattr(item, 'estado', None) or 'PENDIENTE').upper() == 'CONFIRMADO':
            return jsonify({"success": False, "mensaje": "Este producto ya está confirmado."}), 400

        if 'cantidad' in datos and datos['cantidad'] is not None:
            item.cantidad = float(datos['cantidad'])
        if 'precio' in datos and datos['precio'] is not None:
            item.precio = float(datos['precio'])

        if item.cantidad <= 0 or item.precio < 0:
            return jsonify({"success": False, "mensaje": "Cantidad o precio inválido."}), 400

        item.subtotal = float(item.cantidad) * float(item.precio)
        _aplicar_confirmacion_item_en_inventario(item, sess, Producto)

        item.estado = 'CONFIRMADO'
        item.confirmado_en = datetime.now()

        compra = item.compra
        _recalcular_estado_compra(compra)
        sess.commit()

        saldos_actualizados = _obtener_saldos_socios_actuales(sess)
        return jsonify({
            "success": True,
            "mensaje": f"'{item.nombre}' confirmado e ingresado al inventario. Se rebajaron ${item.subtotal:.2f} del saldo.",
            "saldos_socios": saldos_actualizados
        })
    except Exception as e:
        sess.rollback()
        return jsonify({"success": False, "mensaje": f"Error al confirmar: {str(e)}"}), 500


@compras_bp.route('/api/compras/items/<int:item_id>/no-comprado', methods=['POST'])
def marcar_item_no_comprado(item_id):
    from app import ItemCompra
    _, sess = _get_db_y_session()

    try:
        item = sess.get(ItemCompra, item_id)
        if not item:
            return jsonify({"success": False, "mensaje": "Ítem de compra no encontrado."}), 404

        if (getattr(item, 'estado', None) or 'PENDIENTE').upper() == 'CONFIRMADO':
            return jsonify({"success": False, "mensaje": "Este producto ya está confirmado."}), 400

        item.estado = 'NO_COMPRADO'
        compra = item.compra
        _recalcular_estado_compra(compra)
        sess.commit()

        saldos_actualizados = _obtener_saldos_socios_actuales(sess)
        return jsonify({
            "success": True,
            "mensaje": f"'{item.nombre}' marcado como no comprado.",
            "saldos_socios": saldos_actualizados
        })
    except Exception as e:
        sess.rollback()
        return jsonify({"success": False, "mensaje": f"Error al actualizar estado: {str(e)}"}), 500


@compras_bp.route('/api/historial_compras', methods=['GET'])
def obtener_historial_compras():
    from app import Compra, Propietario
    _, sess = _get_db_y_session()

    try:
        compras = sess.query(Compra).order_by(Compra.id.desc()).all()
        resultado = []

        for c in compras:
            proveedores_dict = {}
            for item in c.items:
                prov_nombre = item.proveedor
                if prov_nombre not in proveedores_dict:
                    proveedores_dict[prov_nombre] = {
                        'proveedor': prov_nombre,
                        'productos': [],
                        'total_proveedor': 0.0
                    }
                estado_item = (getattr(item, 'estado', None) or 'PENDIENTE').upper()
                proveedores_dict[prov_nombre]['productos'].append({
                    'id': item.id,
                    'producto': item.nombre,
                    'cantidad': item.cantidad,
                    'precio': item.precio,
                    'subtotal': item.subtotal,
                    'estado': estado_item
                })
                if estado_item != 'NO_COMPRADO':
                    proveedores_dict[prov_nombre]['total_proveedor'] += item.subtotal

            socio_nombre = "No especificado"
            if hasattr(c, 'propietario_id') and c.propietario_id:
                prop = sess.get(Propietario, c.propietario_id)
                if prop:
                    socio_nombre = prop.nombre

            fecha_str = c.fecha.strftime('%d/%m/%Y %I:%M %p') if hasattr(c, 'fecha') and c.fecha else f"Compra #{c.id}"
            estado_compra = (getattr(c, 'estado', None) or 'PLANIFICADA').upper()
            total_confirmado = float(getattr(c, 'total_confirmado', 0.0) or 0.0)

            resultado.append({
                'id': c.id,
                'fecha': fecha_str,
                'socio': socio_nombre,
                'metodo_pago': getattr(c, 'metodo_pago', 'EFECTIVO'),
                'efectivo_inicial': c.efectivo_inicial,
                'total_compra': c.total_compra,
                'total_confirmado': total_confirmado,
                'estado': estado_compra,
                'por_proveedor': list(proveedores_dict.values())
            })

        return jsonify(resultado)
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"Error al cargar historial: {str(e)}"}), 500


@compras_bp.route('/api/compras/<int:compra_id>', methods=['DELETE'])
def eliminar_compra(compra_id):
    from app import Compra, ItemCompra, Producto
    _, sess = _get_db_y_session()

    try:
        compra = sess.get(Compra, compra_id)
        if not compra:
            return jsonify({
                "success": True,
                "mensaje": "La compra ya fue eliminada.",
                "saldos_socios": _obtener_saldos_socios_actuales(sess)
            })

        for item in compra.items:
            if (getattr(item, 'estado', None) or 'PENDIENTE').upper() == 'CONFIRMADO':
                prod = sess.query(Producto).filter(Producto.nombre.ilike(item.nombre.strip())).first()
                if prod:
                    restar_stock(prod, item.cantidad)

        sess.query(ItemCompra).filter_by(compra_id=compra.id).delete()
        sess.delete(compra)
        sess.commit()

        return jsonify({
            "success": True,
            "mensaje": "¡Compra eliminada y stock confirmado revertido correctamente!",
            "saldos_socios": _obtener_saldos_socios_actuales(sess)
        })
    except Exception as e:
        sess.rollback()
        return jsonify({"success": False, "mensaje": f"Error al eliminar: {str(e)}"}), 500