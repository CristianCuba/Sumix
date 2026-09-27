from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify

compras_bp = Blueprint('compras', __name__, template_folder='templates')

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


@compras_bp.route('/compras', methods=['GET'])
def vista_compras():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    from app import Proveedor, Propietario, Producto, Compra, MovimientoCapital, PrestamoTercero, CierreDia, app

    with app.app_context():
        proveedores = Proveedor.query.all()
        propietarios = Propietario.query.all()
        productos = Producto.query.all()

        saldos_socios = {}
        for prop in propietarios:
            # 1. Movimientos de Capital (Inyecciones / Retiros)
            movs = MovimientoCapital.query.filter_by(propietario_id=prop.id).all()
            inyecciones_efectivo = sum(m.monto for m in movs if m.tipo == 'INYECCION' and (not getattr(m, 'metodo_pago', None) or m.metodo_pago == 'EFECTIVO'))
            retiros_efectivo = sum(m.monto for m in movs if m.tipo == 'RETIRO' and (not getattr(m, 'metodo_pago', None) or m.metodo_pago == 'EFECTIVO'))
            inyecciones_transf = sum(m.monto for m in movs if m.tipo == 'INYECCION' and getattr(m, 'metodo_pago', None) == 'TRANSFERENCIA')
            retiros_transf = sum(m.monto for m in movs if m.tipo == 'RETIRO' and getattr(m, 'metodo_pago', None) == 'TRANSFERENCIA')

            # 2. Préstamos Otorgados a terceros
            prestamos = PrestamoTercero.query.filter_by(propietario_id=prop.id, estado='PENDIENTE').all()
            prestamos_efectivo = sum(p.saldo_pendiente for p in prestamos if not getattr(p, 'metodo_pago', None) or p.metodo_pago == 'EFECTIVO')
            prestamos_transf = sum(p.saldo_pendiente for p in prestamos if getattr(p, 'metodo_pago', None) == 'TRANSFERENCIA')

            # 3. Compras realizadas por este socio
            compras_socio = Compra.query.filter_by(propietario_id=prop.id).all()
            compras_efectivo = sum(c.total_compra for c in compras_socio if getattr(c, 'metodo_pago', 'EFECTIVO') == 'EFECTIVO' or not getattr(c, 'metodo_pago', None))
            compras_transf = sum(c.total_compra for c in compras_socio if getattr(c, 'metodo_pago', None) == 'TRANSFERENCIA')

            # 4. Ventas acumuladas en Cierres de caja
            efectivo_acumulado = 0.0
            transferencias_cierres = 0.0
            es_cristian = 'CRISTIAN' in prop.nombre.upper()

            cierres = CierreDia.query.all()
            for c in cierres:
                if hasattr(c, 'detalles'):
                    for d in c.detalles:
                        prod = Producto.query.get(d.producto_id)
                        if prod and prod.propietario_id == prop.id:
                            efectivo_acumulado += (d.subtotal or 0.0)

                if es_cristian and hasattr(c, 'total_transferencias') and c.total_transferencias:
                    transferencias_cierres += (c.total_transferencias or 0.0)

            # Saldos líquidos finales
            efectivo_liquido = max(0.0, efectivo_acumulado + inyecciones_efectivo - retiros_efectivo - prestamos_efectivo - compras_efectivo)
            transferencias_acumuladas = max(0.0, transferencias_cierres + inyecciones_transf - retiros_transf - prestamos_transf - compras_transf)

            # Usar string en la clave del diccionario para coincidencia en JSON
            saldos_socios[str(prop.id)] = {
                'efectivo': efectivo_liquido,
                'transferencia': transferencias_acumuladas
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
    from app import db, Compra, ItemCompra, Producto, obtener_stock_total, app
    datos = request.json or {}

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

    try:
        with app.app_context():
            # 1. Crear registro de la Compra
            nueva_compra = Compra(
                propietario_id=int(propietario_id),
                metodo_pago=metodo_pago,
                efectivo_inicial=efectivo_inicial,
                total_compra=total_compra,
                efectivo_restante=efectivo_restante
            )
            db.session.add(nueva_compra)
            db.session.flush()

            # 2. Registrar ítems y actualizar inventario con Costo Promedio Ponderado
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
                    subtotal=float(item['subtotal'])
                )
                db.session.add(nuevo_item)

                # Buscar producto en inventario
                prod = Producto.query.filter(Producto.nombre.ilike(nombre_prod)).first()
                if prod:
                    # a) Obtener stock y costo antes de ingresar la nueva mercancía
                    try:
                        stock_actual = float(obtener_stock_total(prod) or 0)
                    except Exception:
                        stock_actual = 0.0

                    costo_actual = float(prod.precio_costo or 0.0)

                    # b) Si hay stock previo y costo registrado, calculamos el Promedio Ponderado
                    if stock_actual > 0 and costo_actual > 0:
                        valor_inventario_existente = stock_actual * costo_actual
                        valor_nueva_compra = cant * precio_u
                        nuevo_stock_total = stock_actual + cant

                        costo_ponderado = (valor_inventario_existente + valor_nueva_compra) / nuevo_stock_total
                        prod.precio_costo = round(costo_ponderado, 2)
                    else:
                        # Si el stock era 0 o no tenía costo previo, toma el precio de la nueva compra
                        prod.precio_costo = precio_u

                    # c) Sumar las nuevas unidades físicas al inventario
                    aumentar_stock(prod, cant)

            db.session.commit()

        return jsonify({"success": True, "mensaje": "¡Compra registrada! Stock e Invertido a Costo (Ponderado) actualizados correctamente."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": f"Error al guardar: {str(e)}"}), 500


@compras_bp.route('/api/historial_compras', methods=['GET'])
def obtener_historial_compras():
    from app import Compra, Propietario, app
    try:
        with app.app_context():
            compras = Compra.query.order_by(Compra.id.desc()).all()
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
                    proveedores_dict[prov_nombre]['productos'].append({
                        'producto': item.nombre,
                        'cantidad': item.cantidad,
                        'precio': item.precio,
                        'subtotal': item.subtotal
                    })
                    proveedores_dict[prov_nombre]['total_proveedor'] += item.subtotal

                socio_nombre = "No especificado"
                if hasattr(c, 'propietario_id') and c.propietario_id:
                    prop = Propietario.query.get(c.propietario_id)
                    if prop:
                        socio_nombre = prop.nombre

                fecha_str = c.fecha.strftime('%d/%m/%Y %I:%M %p') if hasattr(c, 'fecha') and c.fecha else f"Compra #{c.id}"

                resultado.append({
                    'id': c.id,
                    'fecha': fecha_str,
                    'socio': socio_nombre,
                    'metodo_pago': getattr(c, 'metodo_pago', 'EFECTIVO'),
                    'efectivo_inicial': c.efectivo_inicial,
                    'total_compra': c.total_compra,
                    'por_proveedor': list(proveedores_dict.values())
                })

        return jsonify(resultado)
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"Error al cargar historial: {str(e)}"}), 500


@compras_bp.route('/api/compras/<int:compra_id>', methods=['DELETE'])
def eliminar_compra(compra_id):
    from app import db, Compra, ItemCompra, Producto, app
    try:
        with app.app_context():
            compra = Compra.query.get(compra_id)
            if not compra:
                return jsonify({"success": True, "mensaje": "La compra ya fue eliminada."})

            # Revertir stock ingresado
            for item in compra.items:
                prod = Producto.query.filter(Producto.nombre.ilike(item.nombre.strip())).first()
                if prod:
                    restar_stock(prod, item.cantidad)

            ItemCompra.query.filter_by(compra_id=compra.id).delete()
            db.session.delete(compra)
            db.session.commit()

        return jsonify({"success": True, "mensaje": "¡Compra eliminada y stock revertido correctamente!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": f"Error al eliminar: {str(e)}"}), 500