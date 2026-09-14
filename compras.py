from flask import Blueprint, render_template, request, jsonify

compras_bp = Blueprint('compras', __name__, template_folder='templates')

@compras_bp.route('/compras', methods=['GET'])
def vista_compras():
    from app import db, Proveedor, app
    with app.app_context():
        proveedores = Proveedor.query.all()
    return render_template('compras.html', proveedores=proveedores)

@compras_bp.route('/api/guardar_compra', methods=['POST'])
def guardar_compra():
    from app import db, Compra, ItemCompra, app
    datos = request.json
    
    efectivo_inicial = float(datos.get('efectivo_inicial', 0))
    items_compra = datos.get('items', [])
    
    if not items_compra:
        return jsonify({"success": False, "mensaje": "La lista de compra está vacía."}), 400
    
    total_compra = sum(float(item['subtotal']) for item in items_compra)
    efectivo_restante = efectivo_inicial - total_compra

    try:
        with app.app_context():
            # Crear la cabecera de la compra
            nueva_compra = Compra(
                efectivo_inicial=efectivo_inicial,
                total_compra=total_compra,
                efectivo_restante=efectivo_restante
            )
            db.session.add(nueva_compra)
            db.session.flush() # Para obtener el ID generado de la compra
            
            # Registrar cada producto asociado
            for item in items_compra:
                nuevo_item = ItemCompra(
                    compra_id=nueva_compra.id,
                    nombre=item['nombre'],
                    proveedor=item['proveedor'],
                    cantidad=float(item['cantidad']),
                    precio=float(item['precio']),
                    subtotal=float(item['subtotal'])
                )
                db.session.add(nuevo_item)
            
            db.session.commit()
            
        return jsonify({"success": True, "mensaje": "¡Compra guardada con éxito en la base de datos!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": f"Error al guardar: {str(e)}"}), 500

@compras_bp.route('/api/historial_compras', methods=['GET'])
def obtener_historial_compras():
    from app import db, Compra, app
    try:
        with app.app_context():
            compras = Compra.query.order_by(Compra.id.desc()).all()
            resultado = []
            
            for c in compras:
                # Agrupar los ítems por proveedor para que se visualicen ordenados
                proveedores_dict = {}
                for item in c.items: # Asumiendo la relación backref='items' o tu relación definida
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
                
                # Formatear la fecha o usar el ID si no guardas la fecha exacta en formato string
                fecha_str = c.fecha.strftime('%Y-%m-%d %H:%M') if hasattr(c, 'fecha') and c.fecha else f"Compra #{c.id}"
                
                resultado.append({
                    'id': c.id,
                    'fecha': fecha_str,
                    'efectivo_inicial': c.efectivo_inicial,
                    'total_compra': c.total_compra,
                    'por_proveedor': list(proveedores_dict.values())
                })
                
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"success": False, "mensaje": f"Error al cargar historial: {str(e)}"}), 500
    
@compras_bp.route('/api/compras/<int:compra_id>', methods=['DELETE'])
def eliminar_compra(compra_id):
    from app import db, Compra, ItemCompra, app
    try:
        with app.app_context():
            compra = Compra.query.get(compra_id)
            if not compra:
                # Si ya fue eliminada (por doble clic), respondemos éxito para que la interfaz se refresque sola
                return jsonify({"success": True, "mensaje": "La compra ya fue eliminada."})
            
            # Eliminar explícitamente los ítems asociados
            ItemCompra.query.filter_by(compra_id=compra.id).delete()
            
            # Eliminar la compra principal
            db.session.delete(compra)
            db.session.commit()
            
        return jsonify({"success": True, "mensaje": "¡Compra eliminada con éxito!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": f"Error al eliminar: {str(e)}"}), 500