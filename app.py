import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
import time
from datetime import datetime  # Si la usas en otras partes
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sumix.db'
app.config['SECRET_KEY'] = 'tu_clave_secreta'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------------------------------------------------#
# MODELOS DE BASE DE DATOS
# -----------------------------------------------------------------#

class Almacen(db.Model):
    __tablename__ = 'almacenes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    ubicacion = db.Column(db.String(150), nullable=True)
    es_area_venta = db.Column(db.Boolean, default=False)
    
    # Relación con Stocks
    stocks = db.relationship('StockAlmacen', backref='almacen', cascade="all, delete-orphan", lazy=True)


class Proveedor(db.Model):
    __tablename__ = 'proveedores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    telefono = db.Column(db.String(30), nullable=True)
    contacto = db.Column(db.String(100), nullable=True)
    
    # NOTA: La relación con Productos se declara dinámicamente en 'Producto'
    # mediante 'backref=db.backref("productos", lazy=True)'


class StockAlmacen(db.Model):
    __tablename__ = 'stock_almacen'
    id = db.Column(db.Integer, primary_key=True)
    # APUNTE: 'productos.id' con 's' porque la tabla se llama 'productos'
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    almacen_id = db.Column(db.Integer, db.ForeignKey('almacenes.id'), nullable=False)
    cantidad = db.Column(db.Float, default=0.0)


class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    unidad_medida = db.Column(db.String(20), default='unidad')
    
    # Precios
    precio_costo = db.Column(db.Float, default=0.0)
    precio_venta = db.Column(db.Float, default=0.0)
    
    # Relación con Proveedor (Corregida para evitar choques)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=True)
    proveedor = db.relationship('Proveedor', backref=db.backref('productos', lazy=True))
    
    # Cuentas por Pagar
    estado_pago = db.Column(db.String(20), default="Pagado")
    monto_pendiente = db.Column(db.Float, default=0.0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con existencias en almacenes
    stocks = db.relationship('StockAlmacen', backref='producto', cascade="all, delete-orphan", lazy=True)

    @property
    def cantidad_total(self):
        return sum(s.cantidad for s in self.stocks)
    
    @property
    def stock_venta(self):
        # Búsqueda optimizada en memoria para no saturar la BD
        for s in self.stocks:
            if s.almacen and s.almacen.es_area_venta:
                return s.cantidad
        return 0.0


class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), default='dependiente')


class Movimiento(db.Model):
    __tablename__ = 'movimientos'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    tipo_movimiento = db.Column(db.String(20), nullable=False) # 'entrada', 'salida', 'traslado'
    concepto = db.Column(db.String(50), nullable=False) # 'Compra', 'Venta', 'Merma', 'Traslado'
    cantidad = db.Column(db.Float, nullable=False)
    origen = db.Column(db.String(50), nullable=True)
    destino = db.Column(db.String(50), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


class CierreDia(db.Model):
    __tablename__ = 'cierres_dia'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_nombre = db.Column(db.String(100), nullable=False)
    total_esperado = db.Column(db.Float, default=0.0)
    efectivo_caja = db.Column(db.Float, default=0.0)
    diferencia = db.Column(db.Float, default=0.0)
    detalles = db.relationship('DetalleCierre', backref='cierre', lazy=True)


class DetalleCierre(db.Model):
    __tablename__ = 'detalles_cierre'
    id = db.Column(db.Integer, primary_key=True)
    cierre_id = db.Column(db.Integer, db.ForeignKey('cierres_dia.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    nombre_producto = db.Column(db.String(100), nullable=False)
    precio_venta = db.Column(db.Float, default=0.0)
    stock_inicial = db.Column(db.Float, default=0.0)
    entradas = db.Column(db.Float, default=0.0)
    stock_final = db.Column(db.Float, default=0.0)
    vendidos = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, default=0.0)

class TipoOperacion(db.Model):
    __tablename__ = 'tipos_operacion'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False) # Ej: "Traslado Interno", "Entrada de Inventario", "Salida / Ajuste"
    codigo = db.Column(db.String(20), unique=True, nullable=False) # 'traslado', 'entrada', 'salida'
    
    # Comportamiento del tipo de operación:
    # 'traslado' -> Requiere Origen y Destino
    # 'entrada'  -> Solo requiere Destino
    # 'salida'   -> Solo requiere Origen
    requiere_origen = db.Column(db.Boolean, default=True)
    requiere_destino = db.Column(db.Boolean, default=True)

    conceptos = db.relationship('ConceptoMovimiento', backref='tipo', cascade='all, delete-orphan', lazy=True)


class ConceptoMovimiento(db.Model):
    __tablename__ = 'conceptos_movimiento'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo_id = db.Column(db.Integer, db.ForeignKey('tipos_operacion.id'), nullable=False)
# -----------------------------------------------------------------#
# CONTROL DE RUTAS Y NAVEGACIÓN
# -----------------------------------------------------------------#
from flask import jsonify

@app.route('/api/tipos_operacion', methods=['GET'])
def api_tipos_operacion():
    # Obtener todos los tipos de operación registrados
    tipos = TipoOperacion.query.all()
    return jsonify([{'id': t.id, 'nombre': t.nombre} for t in tipos])

@app.route('/api/conceptos/<int:tipo_id>', methods=['GET'])
def api_conceptos_por_tipo(tipo_id):
    # Obtener únicamente los conceptos pertenecientes al tipo_id seleccionado
    conceptos = ConceptoMovimiento.query.filter_by(tipo_id=tipo_id).all()
    return jsonify([{'id': c.id, 'nombre': c.nombre} for c in conceptos])


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
# -----------------------------------------------------------------#
# GESTIÓN DE ALMACENES Y PROVEEDORES
# -----------------------------------------------------------------#
# --- RUTAS DE GESTIÓN DE CONCEPTOS ---

# --- RUTAS DE GESTIÓN DE TIPOS DE OPERACIÓN Y CONCEPTOS ---

@app.route('/admin/tipo-operacion/nuevo', methods=['POST'])
def guardar_tipo_operacion():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    nombre = request.form.get('nombre')
    comportamiento = request.form.get('comportamiento') # 'traslado', 'entrada', 'salida'

    if nombre and comportamiento:
        codigo = comportamiento.lower() + "_" + str(int(time.time()))
        
        req_origen = comportamiento in ['traslado', 'salida']
        req_destino = comportamiento in ['traslado', 'entrada']

        nuevo_tipo = TipoOperacion(
            nombre=nombre.strip(),
            codigo=codigo,
            requiere_origen=req_origen,
            requiere_destino=req_destino
        )
        db.session.add(nuevo_tipo)
        db.session.commit()
        flash("Tipo de operación creado exitosamente", "info")

    return redirect(url_for('vista_gestion_entidades'))


@app.route('/admin/tipo-operacion/eliminar/<int:id>', methods=['POST'])
def eliminar_tipo_operacion(id):
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    tipo = TipoOperacion.query.get_or_404(id)
    db.session.delete(tipo)
    db.session.commit()
    flash("Tipo de operación eliminado", "info")
    return redirect(url_for('vista_gestion_entidades'))


@app.route('/admin/concepto/nuevo', methods=['POST'])
def guardar_concepto():
    nombre = request.form.get('nombre')
    tipo_id = request.form.get('tipo_id')

    # Instanciar ÚNICAMENTE con los campos válidos del modelo
    nuevo_concepto = ConceptoMovimiento(
        nombre=nombre,
        tipo_id=int(tipo_id) if tipo_id else None
    )

    db.session.add(nuevo_concepto)
    db.session.commit()

    return redirect(url_for('vista_gestion_entidades'))


@app.route('/admin/concepto/eliminar/<int:id>', methods=['POST'])
def eliminar_concepto(id):
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    concepto = ConceptoMovimiento.query.get_or_404(id)
    db.session.delete(concepto)
    db.session.commit()
    flash("Concepto eliminado", "info")
    return redirect(url_for('vista_gestion_entidades'))


# --- API JSON PARA MODAL DINÁMICO ---

@app.route('/api/tipos-operacion')
def api_obtener_tipos_operacion():
    tipos = TipoOperacion.query.all()
    res = []
    for t in tipos:
        res.append({
            'id': t.id,
            'nombre': t.nombre,
            'requiere_origen': t.requiere_origen,
            'requiere_destino': t.requiere_destino,
            'conceptos': [{'id': c.id, 'nombre': c.nombre} for c in t.conceptos]
        })
    return jsonify(res)
@app.route('/admin/gestion-entidades', methods=['GET'])
def vista_gestion_entidades():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    almacenes = Almacen.query.all()
    proveedores = Proveedor.query.all()
    tipos_operacion = TipoOperacion.query.all()
    conceptos = ConceptoMovimiento.query.all()

    return render_template(
        'admin_gestion.html',
        almacenes=almacenes,
        proveedores=proveedores,
        tipos_operacion=tipos_operacion,
        conceptos=conceptos
    )

@app.route('/admin/almacen/nuevo', methods=['POST'])
def guardar_almacen():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    nombre = request.form.get('nombre')
    ubicacion = request.form.get('ubicacion')
    es_area_venta = 'es_area_venta' in request.form

    if Almacen.query.filter_by(nombre=nombre).first():
        flash("Ya existe un almacén con ese nombre.", "error")
        return redirect(url_for('vista_gestion_entidades'))

    nuevo_almacen = Almacen(nombre=nombre, ubicacion=ubicacion, es_area_venta=es_area_venta)
    db.session.add(nuevo_almacen)
    db.session.commit()
    flash("Almacén registrado con éxito", "info")
    return redirect(url_for('vista_gestion_entidades'))


@app.route('/admin/almacen/eliminar/<int:id>', methods=['POST'])
def eliminar_almacen(id):
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    almacen = Almacen.query.get_or_404(id)
    db.session.delete(almacen)
    db.session.commit()
    return redirect(url_for('vista_gestion_entidades'))


@app.route('/admin/proveedor/nuevo', methods=['POST'])
def guardar_proveedor():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    nombre = request.form.get('nombre')
    telefono = request.form.get('telefono')
    contacto = request.form.get('contacto')

    if Proveedor.query.filter_by(nombre=nombre).first():
        flash("Ya existe un proveedor con ese nombre.", "error")
        return redirect(url_for('vista_gestion_entidades'))

    nuevo_proveedor = Proveedor(nombre=nombre, telefono=telefono, contacto=contacto)
    db.session.add(nuevo_proveedor)
    db.session.commit()
    flash("Proveedor registrado con éxito", "info")
    return redirect(url_for('vista_gestion_entidades'))


@app.route('/admin/proveedor/eliminar/<int:id>', methods=['POST'])
def eliminar_proveedor(id):
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    proveedor = Proveedor.query.get_or_404(id)
    db.session.delete(proveedor)
    db.session.commit()
    return redirect(url_for('vista_gestion_entidades'))

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
    # Validar sesión de administrador
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    # 1. Obtener los tipos de operación creados dinámicamente
    tipos_operaciones = TipoOperacion.query.all()
    
    # 2. Obtener la lista general de almacenes y productos
    almacenes = Almacen.query.all()
    productos = Producto.query.all()
    
    # 3. Obtener todos los conceptos registrados
    conceptos = ConceptoMovimiento.query.all()

    # Renderizar la vista pasando todas las variables necesarias al template
    return render_template(
        'admin_almacenes.html',
        tipos_operaciones=tipos_operaciones,
        almacenes=almacenes,
        productos=productos,
        conceptos=conceptos
    )

@app.route('/guardar_producto', methods=['POST'])
def guardar_producto():
    # 1. Obtener datos del formulario
    nombre = request.form.get('nombre')
    precio_costo = float(request.form.get('precio_costo', 0))
    precio_venta = float(request.form.get('precio_venta', 0))
    proveedor_id = request.form.get('proveedor_id')  # ID del select de proveedores
    almacen_id = request.form.get('almacen_id')      # ID del select de almacenes
    cantidad_inicial = float(request.form.get('cantidad', 0))

    # 2. Crear el Producto
    nuevo_producto = Producto(
        nombre=nombre,
        precio_costo=precio_costo,
        precio_venta=precio_venta,
        proveedor_id=int(proveedor_id) if proveedor_id else None
    )
    db.session.add(nuevo_producto)
    db.session.flush()  # Para obtener el ID generado del nuevo_producto

    # 3. Crear el registro en StockAlmacen (VINCULA EL ALMACÉN Y LA CANTIDAD)
    if almacen_id:
        nuevo_stock = StockAlmacen(
            producto_id=nuevo_producto.id,
            almacen_id=int(almacen_id),
            cantidad=cantidad_inicial
        )
        db.session.add(nuevo_stock)

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
    print("\n--- [DEBUG] DATOS RECIBIDOS DEL FORMULARIO ---")
    for key, value in request.form.items():
        print(f"  {key}: {repr(value)}")
    print("---------------------------------------------\n")

    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    producto_id = int(request.form.get('producto_id'))
    tipo_op_id = request.form.get('tipo_operacion', '')  # Llega el ID de TipoOperacion
    concepto = request.form.get('concepto')
    cantidad = float(request.form.get('cantidad') or 0.0)

    if cantidad <= 0:
        flash("La cantidad debe ser mayor a cero.", "error")
        return redirect(url_for('vista_admin'))

    producto = Producto.query.get_or_404(producto_id)

    # 1. Obtener la entidad de TipoOperacion para extraer su 'codigo' ('traslado', 'entrada', 'salida')
    tipo_operacion_obj = TipoOperacion.query.get(tipo_op_id) if tipo_op_id else None

    if not tipo_operacion_obj:
        print("ERR: No se encontró TipoOperacion con ID:", tipo_op_id)
        flash("Tipo de operación inválido.", "error")
        return redirect(url_for('vista_admin'))

    tipo_op = tipo_operacion_obj.codigo.lower().strip()
    print(f"--> CÓDIGO DETECTADO: '{tipo_op}'")  # REVISAR ESTE PRINT EN LA CONSOLA

    def get_or_create_stock(almacen_id):
        stock = StockAlmacen.query.filter_by(
            producto_id=producto.id, 
            almacen_id=almacen_id
        ).first()
        if not stock:
            stock = StockAlmacen(producto_id=producto.id, almacen_id=almacen_id, cantidad=0.0)
            db.session.add(stock)
        return stock

    origen_nombre = None
    destino_nombre = None

    if tipo_op == 'entrada':
        destino_id = request.form.get('ubicacion_destino')
        if destino_id:
            almacen_dest = Almacen.query.get(int(destino_id))
            if almacen_dest:
                stk_destino = get_or_create_stock(almacen_dest.id)
                stk_destino.cantidad += cantidad
                destino_nombre = almacen_dest.nombre

    elif tipo_op == 'salida':
        origen_id = request.form.get('ubicacion_origen')
        destino_input = request.form.get('ubicacion_destino')

        if origen_id:
            almacen_orig = Almacen.query.get(int(origen_id))
            if almacen_orig:
                stk_origen = get_or_create_stock(almacen_orig.id)
                stk_origen.cantidad = max(0.0, stk_origen.cantidad - cantidad)
                origen_nombre = almacen_orig.nombre

        if destino_input:
            if destino_input.isdigit():
                almacen_dest = Almacen.query.get(int(destino_input))
                destino_nombre = almacen_dest.nombre if almacen_dest else destino_input
            else:
                destino_nombre = destino_input

    elif tipo_op == 'traslado':
        origen_id = request.form.get('ubicacion_origen')
        destino_id = request.form.get('ubicacion_destino')

        if origen_id and destino_id and origen_id != destino_id:
            almacen_orig = Almacen.query.get(int(origen_id))
            almacen_dest = Almacen.query.get(int(destino_id))

            if almacen_orig and almacen_dest:
                stk_origen = get_or_create_stock(almacen_orig.id)
                stk_destino = get_or_create_stock(almacen_dest.id)

                # Descontar del origen y sumar exacto al destino
                stk_origen.cantidad = max(0.0, stk_origen.cantidad - cantidad)
                stk_destino.cantidad += cantidad

                origen_nombre = almacen_orig.nombre
                destino_nombre = almacen_dest.nombre

    # 2. Registrar trazabilidad del movimiento
    log_mov = Movimiento(
        producto_id=producto.id,
        tipo_movimiento=tipo_op,
        concepto=concepto,
        cantidad=cantidad,
        origen=origen_nombre,
        destino=destino_nombre
    )

    db.session.add(log_mov)
    db.session.commit()

    flash("Movimiento registrado con éxito.", "info")
    return redirect(url_for('vista_admin'))


@app.route('/api/conceptos/<int:tipo_id>', methods=['GET'])
def obtener_conceptos_por_tipo(tipo_id):
    try:
        # Se corrigió tipo_operacion_id por tipo_id para coincidir con el modelo ConceptoMovimiento
        conceptos = ConceptoMovimiento.query.filter_by(tipo_id=tipo_id).all()
        data = [{'id': c.id, 'nombre': c.nombre} for c in conceptos]
        return jsonify(data), 200
    except Exception as e:
        print(f"Error al obtener conceptos: {e}")
        return jsonify({'error': 'Error interno al consultar conceptos'}), 500
# -----------------------------------------------------------------#
# RESPALDO Y RESTAURACIÓN DE BASE DE DATOS
# -----------------------------------------------------------------#

DB_NAME = 'sumix.db'

@app.route('/admin/exportar-db')
def exportar_db():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    try:
        # Buscar en la carpeta 'instance'
        db_path = os.path.join(app.root_path, 'instance', DB_NAME)
        
        # Si no existe en 'instance', buscar en la raíz del proyecto
        if not os.path.exists(db_path):
            db_path = os.path.join(app.root_path, DB_NAME)

        if not os.path.exists(db_path):
            flash("No se encontró el archivo de la base de datos.", "error")
            return redirect(url_for('vista_gestion_entidades'))

        # Genera el archivo para descargar
        return send_file(
            db_path,
            as_attachment=True,
            download_name=f"respaldo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
    except Exception as e:
        flash(f"Error al exportar la base de datos: {str(e)}", "error")
        return redirect(url_for('vista_gestion_entidades'))


@app.route('/admin/importar-db', methods=['POST'])
def importar_db():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    if 'archivo_db' not in request.files:
        flash("No se seleccionó ningún archivo.", "error")
        return redirect(url_for('vista_gestion_entidades'))
        
    file = request.files['archivo_db']
    
    if file.filename == '':
        flash("No se seleccionó ningún archivo.", "error")
        return redirect(url_for('vista_gestion_entidades'))

    if file and (file.filename.endswith('.db') or file.filename.endswith('.sqlite')):
        # Determinar la ubicación de destino
        db_path = os.path.join(app.root_path, 'instance', DB_NAME)
        if not os.path.exists(db_path):
            db_path = os.path.join(app.root_path, DB_NAME)

        # Cerrar las conexiones activas antes de sobrescribir el archivo
        db.session.remove()
        db.engine.dispose()

        # Guardar y reemplazar la base de datos
        file.save(db_path)
        flash("¡Base de datos restaurada con éxito! Reinicia la sesión si es necesario.", "info")
    else:
        flash("Formato de archivo no válido. Debe ser un archivo .db o .sqlite", "error")

    return redirect(url_for('vista_gestion_entidades'))

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
    