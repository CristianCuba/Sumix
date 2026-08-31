from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sumix.db'
app.config['SECRET_KEY'] = 'tu_clave_secreta'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------------------------------------------------#
# MODELOS DE BASE DE DATOS
# -----------------------------------------------------------------#

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    unidad_medida = db.Column(db.String(20), default='unidad')
    
    # Stocks por ubicación
    stock_almacen1 = db.Column(db.Float, default=0.0)
    stock_almacen2 = db.Column(db.Float, default=0.0)
    stock_venta = db.Column(db.Float, default=0.0)
    
    # Precios y Proveedor
    precio_costo = db.Column(db.Float, default=0.0)
    precio_venta = db.Column(db.Float, default=0.0)
    proveedor = db.Column(db.String(100), nullable=True, default="Sin Proveedor")
    
    # Cuentas por Pagar
    estado_pago = db.Column(db.String(20), default="Pagado")  # "Pagado" o "Pendiente"
    monto_pendiente = db.Column(db.Float, default=0.0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def cantidad_total(self):
        return self.stock_almacen1 + self.stock_almacen2 + self.stock_venta


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), default='dependiente')


class Movimiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    tipo_movimiento = db.Column(db.String(20), nullable=False) # 'entrada', 'salida', 'traslado'
    concepto = db.Column(db.String(50), nullable=False) # 'Compra', 'Venta', 'Merma', 'Traslado'
    cantidad = db.Column(db.Float, nullable=False)
    origen = db.Column(db.String(50), nullable=True)
    destino = db.Column(db.String(50), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class CierreDia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    usuario_nombre = db.Column(db.String(100), nullable=False)
    total_esperado = db.Column(db.Float, default=0.0)
    efectivo_caja = db.Column(db.Float, default=0.0)
    diferencia = db.Column(db.Float, default=0.0)
    detalles = db.relationship('DetalleCierre', backref='cierre', lazy=True)

class DetalleCierre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cierre_id = db.Column(db.Integer, db.ForeignKey('cierre_dia.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    nombre_producto = db.Column(db.String(100), nullable=False)
    precio_venta = db.Column(db.Float, default=0.0)
    stock_inicial = db.Column(db.Float, default=0.0)
    entradas = db.Column(db.Float, default=0.0)
    stock_final = db.Column(db.Float, default=0.0)
    vendidos = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, default=0.0) 


# -----------------------------------------------------------------#
# CONTROL DE RUTAS Y NAVEGACIÓN
# -----------------------------------------------------------------#

@app.route('/')
def inicio():
    """Redirige automáticamente según el rol del usuario conectado."""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if session.get('rol') == 'admin':
        return redirect(url_for('vista_admin'))
    else:
        return redirect(url_for('vista_cierre'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Usuario.query.filter_by(username=username, password=password).first()
        
        if user:
            session['user'] = user.username
            session['rol'] = user.rol
            session['nombre'] = user.nombre
            return redirect(url_for('inicio'))
        else:
            flash("Usuario o contraseña incorrectos", "error")
            
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


from sqlalchemy import case

@app.route('/cierre')
def vista_cierre():
    if 'user' not in session:
        return redirect(url_for('login'))

    # ORDENAMIENTO:
    # 1. case(...) evalúa si el stock_venta es 0. Si es 0 le da prioridad 1, si es > 0 le da prioridad 0.
    # 2. Luego ordena alfabéticamente por nombre.
    productos = Producto.query.order_by(
        case((Producto.stock_venta == 0, 1), else_=0),
        Producto.nombre.asc()
    ).all()

    return render_template('cierre.html', productos=productos)


@app.route('/admin')
def vista_admin():
    """Vista exclusiva para el Administrador (Almacenes e Inventario)."""
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
    
    productos = Producto.query.all()
    return render_template('admin_almacenes.html', productos=productos)


@app.route('/guardar_producto', methods=['POST'])
def guardar_producto():
    # 1. Capturar los datos enviados desde el formulario
    nombre = request.form.get('descripcion')
    unidad_medida = request.form.get('unidad_medida', 'unidad')  # <-- Capturar unidad de medida
    cantidad = float(request.form.get('cantidad', 0))
    precio_costo = float(request.form.get('precio_costo', 0))
    precio_venta = float(request.form.get('precio_venta', 0))
    proveedor = request.form.get('proveedor')
    estado_pago = request.form.get('estado_pago')
    almacen_destino = request.form.get('almacen_destino')
    
   
    # 2. Asignar cantidad según el almacén seleccionado
    stock_almacen1 = cantidad if almacen_destino == 'almacen1' else 0.0
    stock_almacen2 = cantidad if almacen_destino == 'almacen2' else 0.0
    stock_venta = cantidad if almacen_destino == 'venta' else 0.0

    # 3. Calcular monto pendiente si aplica
    monto_pendiente = (cantidad * precio_costo) if estado_pago == 'Pendiente' else 0.0

    # 4. Crear la instancia de Producto pasando la unidad elegida
    nuevo_producto = Producto(
        nombre=nombre,
        unidad_medida=unidad_medida,  # <-- Se asigna la unidad recibida del formulario
        precio_costo=precio_costo,
        precio_venta=precio_venta,
        proveedor=proveedor if proveedor else "Sin Proveedor",
        stock_almacen1=stock_almacen1,
        stock_almacen2=stock_almacen2,
        stock_venta=stock_venta,
        estado_pago=estado_pago,
        monto_pendiente=monto_pendiente
    )
    
    db.session.add(nuevo_producto)
    db.session.commit()
    
    return redirect(url_for('vista_admin'))
@app.route('/eliminar_producto/<int:id>', methods=['POST'])
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    return redirect(url_for('vista_admin'))
from flask import jsonify

@app.route('/procesar_cierre', methods=['POST'])
def procesar_cierre():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Sesión no iniciada'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Datos inválidos'}), 400

    efectivo_caja = float(data.get('efectivo_caja', 0.0))
    productos_cierre = data.get('productos', [])

    # 1. VALIDACIÓN EN BACKEND: Recalcular el total esperado
    total_esperado = 0.0
    for p_data in productos_cierre:
        subtotal = float(p_data.get('subtotal', 0.0))
        total_esperado += subtotal

    diferencia = efectivo_caja - total_esperado

    # Si hay descuadre (mayor a 1 centavo por redondeo decimal), bloqueamos el guardado
    if abs(diferencia) > 0.01:
        return jsonify({
            'success': False, 
            'message': f'La caja no cuadra. Hay una diferencia de ${diferencia:.2f}. El cierre fue rechazado.'
        }), 400

    # 2. PROCESAR CIERRO EN BD (Tu código actual)
    try:
        nuevo_cierre = CierreDia(
            usuario_nombre=session.get('nombre', session.get('user')),
            efectivo_caja=efectivo_caja,
            total_esperado=total_esperado,
            diferencia=diferencia
        )
        db.session.add(nuevo_cierre)
        db.session.flush()

        for p_data in productos_cierre:
            p_id = int(p_data['id'])
            entradas = float(p_data.get('entradas', 0.0))
            stock_final = float(p_data.get('stock_final', 0.0))
            vendidos = float(p_data.get('vendidos', 0.0))
            subtotal = float(p_data.get('subtotal', 0.0))

            producto = Producto.query.get(p_id)
            if producto:
                detalle = DetalleCierre(
                    cierre_id=nuevo_cierre.id,
                    producto_id=producto.id,
                    nombre_producto=producto.nombre,
                    precio_venta=producto.precio_venta,
                    stock_inicial=producto.stock_venta,
                    entradas=entradas,
                    stock_final=stock_final,
                    vendidos=vendidos,
                    subtotal=subtotal
                )
                db.session.add(detalle)

                if vendidos > 0:
                    mov_salida = Movimiento(
                        producto_id=producto.id,
                        tipo_movimiento='salida',
                        concepto='Venta Cierre Día',
                        cantidad=vendidos,
                        origen='venta',
                        destino=None
                    )
                    db.session.add(mov_salida)

                if entradas > 0:
                    mov_entrada = Movimiento(
                        producto_id=producto.id,
                        tipo_movimiento='entrada',
                        concepto='Entrada Cierre Día',
                        cantidad=entradas,
                        origen=None,
                        destino='venta'
                    )
                    db.session.add(mov_entrada)

                # Actualizar stock para el nuevo turno
                producto.stock_venta = stock_final

        db.session.commit()
        return jsonify({'success': True, 'message': 'Cierre del día completado con éxito'})

    except Exception as e:
        db.session.rollback()
        print(f"Error en procesar_cierre: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500
# -----------------------------------------------------------------#
# CONSULTA DE CIERRES Y REPORTES (ADMIN)
# -----------------------------------------------------------------#

@app.route('/admin/cierres')
def vista_reporte_cierres():
    """Vista con la tabla e historial de cierres de caja realizados."""
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    # Obtener cierres ordenados del más reciente al más antiguo
    cierres = CierreDia.query.order_by(CierreDia.fecha.desc()).all()
    return render_template('admin_cierres.html', cierres=cierres)


@app.route('/admin/cierres/<int:id_cierre>/detalle')
def obtener_detalle_cierre(id_cierre):
    """Devuelve los detalles de un cierre específico en formato JSON para el modal."""
    if 'user' not in session or session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'}), 403

    cierre = CierreDia.query.get_or_404(id_cierre)
    detalles = []

    for d in cierre.detalles:
        detalles.append({
            'nombre_producto': d.nombre_producto,
            'precio_venta': d.precio_venta,
            'stock_inicial': d.stock_inicial,
            'entradas': d.entradas,
            'stock_final': d.stock_final,
            'vendidos': d.vendidos,
            'subtotal': d.subtotal
        })

    return jsonify({
        'success': True,
        'cierre': {
            'id': cierre.id,
            'fecha': cierre.fecha.strftime('%d/%m/%Y %I:%M %p'),
            'usuario_nombre': cierre.usuario_nombre,
            'total_esperado': cierre.total_esperado,
            'efectivo_caja': cierre.efectivo_caja,
            'diferencia': cierre.diferencia
        },
        'detalles': detalles
    })
# -----------------------------------------------------------------#
# CUENTAS POR PAGAR
# -----------------------------------------------------------------#

@app.route('/admin/cuentas-por-pagar')
@app.route('/cuentas-por-pagar')
def cuentas_por_pagar():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    proveedor_filtro = request.args.get('proveedor', '')
    
    # Obtener proveedores con deudas pendientes
    proveedores_query = db.session.query(Producto.proveedor).filter_by(estado_pago='Pendiente').distinct().all()
    lista_proveedores = [p[0] for p in proveedores_query if p[0]]
    
    # Filtrar por proveedor si aplica
    query = Producto.query.filter_by(estado_pago='Pendiente')
    if proveedor_filtro:
        query = query.filter_by(proveedor=proveedor_filtro)
        
    cuentas_pendientes = query.all()
    total_adeudado = sum(item.monto_pendiente for item in cuentas_pendientes)
    
    return render_template(
        'cuentas_por_pagar.html',
        cuentas=cuentas_pendientes,
        proveedores=lista_proveedores,
        proveedor_seleccionado=proveedor_filtro,
        total_adeudado=total_adeudado
    )


@app.route('/pagar-cuenta/<int:id>', methods=['POST'])
def pagar_cuenta(id):
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    producto = Producto.query.get_or_404(id)
    producto.estado_pago = 'Pagado'
    producto.monto_pendiente = 0.0
    db.session.commit()
    flash(f'Cuenta abonada/marcada como pagada para {producto.nombre}', 'info')
    return redirect(url_for('cuentas_por_pagar'))


# -----------------------------------------------------------------#
# GESTIÓN DE USUARIOS
# -----------------------------------------------------------------#

@app.route('/admin/usuarios')
def vista_usuarios():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
    
    usuarios = Usuario.query.all()
    return render_template('admin_usuarios.html', usuarios=usuarios)


@app.route('/admin/usuarios/nuevo', methods=['POST'])
def guardar_usuario():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    username = request.form.get('username')
    nombre = request.form.get('nombre')
    password = request.form.get('password')
    rol = request.form.get('rol')

    if Usuario.query.filter_by(username=username).first():
        flash("El nombre de usuario ya existe.", "error")
        return redirect(url_for('vista_usuarios'))

    nuevo_user = Usuario(
        username=username,
        nombre=nombre,
        password=password,
        rol=rol
    )

    db.session.add(nuevo_user)
    db.session.commit()

    return redirect(url_for('vista_usuarios'))


@app.route('/admin/usuarios/eliminar/<int:id>', methods=['POST'])
def eliminar_usuario(id):
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    user = Usuario.query.get_or_404(id)
    
    if user.username == session.get('user'):
        return redirect(url_for('vista_usuarios'))

    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('vista_usuarios'))


# -----------------------------------------------------------------#
# MOVIMIENTOS E INVENTARIO
# -----------------------------------------------------------------#

@app.route('/admin/producto/movimiento', methods=['POST'])
def registrar_movimiento():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    producto_id = int(request.form.get('producto_id'))
    tipo_op = request.form.get('tipo_operacion') # 'entrada', 'salida', 'traslado'
    concepto = request.form.get('concepto')
    cantidad = float(request.form.get('cantidad') or 0.0)

    producto = Producto.query.get_or_404(producto_id)

    if cantidad <= 0:
        return redirect(url_for('vista_admin'))

    def get_stock(loc):
        if loc == 'almacen1': return producto.stock_almacen1
        if loc == 'almacen2': return producto.stock_almacen2
        if loc == 'venta': return producto.stock_venta
        return 0.0

    def set_stock(loc, valor):
        if loc == 'almacen1': producto.stock_almacen1 = valor
        elif loc == 'almacen2': producto.stock_almacen2 = valor
        elif loc == 'venta': producto.stock_venta = valor

    origen = None
    destino = None

    if tipo_op == 'entrada':
        destino = request.form.get('ubicacion_destino')
        set_stock(destino, get_stock(destino) + cantidad)

    elif tipo_op == 'salida':
        origen = request.form.get('ubicacion_origen')
        stk_actual = get_stock(origen)
        set_stock(origen, max(0.0, stk_actual - cantidad))

    elif tipo_op == 'traslado':
        origen = request.form.get('ubicacion_origen')
        destino = request.form.get('ubicacion_destino')
        
        if origen != destino:
            stk_origen = get_stock(origen)
            descuento = min(stk_origen, cantidad)
            set_stock(origen, stk_origen - descuento)
            set_stock(destino, get_stock(destino) + descuento)

    log_mov = Movimiento(
        producto_id=producto.id,
        tipo_movimiento=tipo_op,
        concepto=concepto,
        cantidad=cantidad,
        origen=origen,
        destino=destino
    )
    db.session.add(log_mov)
    db.session.commit()

    return redirect(url_for('vista_admin'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Crear usuario admin inicial si no existe
        if not Usuario.query.filter_by(username='admin').first():
            admin_init = Usuario(username='admin', password='1234', nombre='Cristhian Hernandez', rol='admin')
            db.session.add(admin_init)
            db.session.commit()
            print("¡Base de datos y usuario admin creados exitosamente!")
            
    app.run(debug=True)