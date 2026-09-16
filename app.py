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

from compras import compras_bp
app.register_blueprint(compras_bp)
# -----------------------------------------------------------------#
# MODELOS DE BASE DE DATOS
# -----------------------------------------------------------------#

class Compra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    efectivo_inicial = db.Column(db.Float, nullable=False)
    total_compra = db.Column(db.Float, nullable=False)
    efectivo_restante = db.Column(db.Float, nullable=False)
    items = db.relationship('ItemCompra', backref='compra', lazy=True, cascade='all, delete-orphan')

class ItemCompra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('compra.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    proveedor = db.Column(db.String(100), nullable=True)
    cantidad = db.Column(db.Float, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    
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

class Propietario(db.Model):
    __tablename__ = 'propietarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.String(200))

    # Relación para acceder a los productos desde el propietario
    productos = db.relationship('Producto', backref='propietario', lazy=True)


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
    propietario_id = db.Column(db.Integer, db.ForeignKey('propietarios.id'), nullable=True)
    
    # Precios
    precio_costo = db.Column(db.Float, default=0.0)
    precio_venta = db.Column(db.Float, default=0.0)
    
    # Control de Caducidad
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    
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


from sqlalchemy.ext.hybrid import hybrid_property # Asegúrate de importarlo si no lo tienes, o usa este bloque directo:

class Usuario(db.Model):
    __tablename__ = 'usuarios'  # <-- ¡Aquí está la clave, en plural!
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(50), nullable=False)  # <-- ¡Aquí está tu columna 'rol'!
    
    # Relación de almacenes si la necesitas
    almacen_id = db.Column(db.Integer, db.ForeignKey('almacenes.id'), nullable=True)
    almacen = db.relationship('Almacen', backref='usuarios')


class CierreDia(db.Model):
    __tablename__ = 'cierres_dia'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_nombre = db.Column(db.String(100), nullable=False)
    total_esperado = db.Column(db.Float, default=0.0)
    efectivo_caja = db.Column(db.Float, default=0.0)
    total_transferencias = db.Column(db.Float, default=0.0)
    total_deudas = db.Column(db.Float, default=0.0) # <--- Nuevo campo para el total de deudas
    diferencia = db.Column(db.Float, default=0.0)
    detalles = db.relationship('DetalleCierre', backref='cierre', lazy=True)
    deudas = db.relationship('DeudaCierre', backref='cierre', lazy=True) # <--- Relación con las deudas del cierre


class DeudaCierre(db.Model):
    __tablename__ = 'deudas_cierre'
    id = db.Column(db.Integer, primary_key=True)
    cierre_id = db.Column(db.Integer, db.ForeignKey('cierres_dia.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    producto_nombre = db.Column(db.String(100), nullable=False)
    concepto = db.Column(db.String(150), nullable=False)
    cantidad = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, default=0.0)


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

class HistorialPago(db.Model):
    __tablename__ = 'historial_pagos'
    id = db.Column(db.Integer, primary_key=True)
    producto_nombre = db.Column(db.String(100), nullable=False)
    proveedor_nombre = db.Column(db.String(100), nullable=True)
    monto_pagado = db.Column(db.Float, nullable=False)
    fecha_pago = db.Column(db.DateTime, default=datetime.utcnow)    
# -----------------------------------------------------------------#
# CONTROL DE RUTAS Y NAVEGACIÓN
# -----------------------------------------------------------------#
from flask import jsonify
from datetime import date

@app.context_processor
def inject_today():
    return {'hoy': date.today()}

@app.route('/pagar_cuenta/<int:id>', methods=['POST'])
def pagar_cuenta(id):
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    producto = Producto.query.get_or_404(id)
    
    if producto.estado_pago == 'Pendiente':
        # 1. Crear el registro en el historial
        nuevo_historial = HistorialPago(
            producto_nombre=producto.nombre,
            proveedor_nombre=producto.proveedor.nombre if producto.proveedor else 'Sin Proveedor',
            monto_pagado=producto.monto_pendiente
        )
        db.session.add(nuevo_historial)

        # 2. Actualizar el producto a Pagado
        producto.estado_pago = 'Pagado'
        producto.monto_pendiente = 0.0

        db.session.commit()

    return redirect(url_for('cuentas_por_pagar'))

@app.route('/api/tipos_operacion', methods=['GET'])
def api_tipos_operacion():
    # Obtener todos los tipos de operación registrados
    tipos = TipoOperacion.query.all()
    return jsonify([{'id': t.id, 'nombre': t.nombre} for t in tipos])

@app.route('/propietarios', methods=['GET', 'POST'])
def gestionar_propietarios():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        
        if nombre:
            nuevo = Propietario(nombre=nombre, descripcion=descripcion)
            db.session.add(nuevo)
            db.session.commit()
            return redirect(url_for('gestionar_propietarios'))

    lista_propietarios = Propietario.query.all()
    return render_template('admin_gestion.html', propietarios=lista_propietarios)


@app.route('/eliminar_propietario/<int:id>')
def eliminar_propietario(id):
    if 'user' in session and session.get('rol') == 'admin':
        p = Propietario.query.get_or_404(id)
        db.session.delete(p)
        db.session.commit()
    return redirect(url_for('gestionar_propietarios'))

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
    propietarios = Propietario.query.all()

    return render_template(
        'admin_gestion.html',
        almacenes=almacenes,
        proveedores=proveedores,
        tipos_operacion=tipos_operacion,
        conceptos=conceptos,
        propietarios = propietarios
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
    username = session.get('user')
    usuario_actual = Usuario.query.filter_by(username=username).first()
    
    if not usuario_actual:
        return redirect(url_for('login'))

    almacen_id = usuario_actual.almacen_id
    productos = Producto.query.all()
    
    for prod in productos:
        stock_alm = StockAlmacen.query.filter_by(
            producto_id=prod.id, 
            almacen_id=almacen_id
        ).first()
        
        cantidad_actual = stock_alm.cantidad if stock_alm else 0.0
        
        prod.stock_en_almacen = cantidad_actual
        prod.stock_final_inicial = cantidad_actual

    # NUEVO: Buscar las deudas registradas en los cierres para que no desaparezcan de la vista
    # (Si quieres filtrarlas por almacén o mostrar todas las activas, puedes ajustarlo aquí)
    deudas_pendientes = DeudaCierre.query.all()

    return render_template('cierre.html', productos=productos, deudas_pendientes=deudas_pendientes)

import json

from datetime import date
from flask import redirect, render_template, request, session, url_for


@app.route("/admin")
def vista_admin():
    if "user" not in session or session.get("rol") != "admin":
        return redirect(url_for("login"))

    # 1. Obtención de colecciones para tablas y selectores
    almacenes = Almacen.query.all()
    proveedores = Proveedor.query.all()
    propietarios = Propietario.query.all()
    tipos_operacion = TipoOperacion.query.all()
    
    conceptos = ConceptoMovimiento.query.all()

    # 💡 Conversión limpia de conceptos a JSON para JavaScript
    conceptos_json = [
        {"id": c.id, "tipo_id": c.tipo_id, "nombre": c.nombre} 
        for c in conceptos
    ]

    # 2. Captura del filtro de propietario desde la URL
    propietario_filtro_id = request.args.get("propietario_id", "todos")

    # 3. Consulta de productos filtrados
    if propietario_filtro_id != "todos" and propietario_filtro_id.isdigit():
        productos = Producto.query.filter_by(
            propietario_id=int(propietario_filtro_id)
        ).all()
    else:
        productos = Producto.query.all()

    # 4. Cálculo de métricas usando las propiedades del modelo Producto
    inversion_stock = 0.0
    valor_venta = 0.0

    for p in productos:
        # Usa la propiedad 'cantidad_total' definida en Producto
        stock_total = p.cantidad_total
        costo = p.precio_costo or 0.0
        precio = p.precio_venta or 0.0

        inversion_stock += costo * stock_total
        valor_venta += precio * stock_total

    ganancia_proyectada = valor_venta - inversion_stock
    efectivo_caja = session.get("efectivo_caja", 0.0)

    # 5. Renderizado alineado exactamente con la plantilla Jinja2
    return render_template(
        "admin_almacenes.html",
        almacenes=almacenes,
        proveedores=proveedores,
        propietarios=propietarios,
        tipos_operacion=tipos_operacion,
        conceptos=conceptos,
        conceptos_json=conceptos_json,  # <--- Variable JSON inyectada
        productos=productos,
        propietario_filtro_id=str(propietario_filtro_id),
        total_invertido=inversion_stock,
        total_venta_estimada=valor_venta,  # Nombre requerido por el HTML
        ganancia_potencial=ganancia_proyectada,  # Nombre requerido por el HTML
        efectivo_caja=efectivo_caja,
        hoy=date.today(),  # Para el cálculo de fecha_vencimiento en el HTML
    )
@app.route('/trasladar_stock', methods=['POST'])
def trasladar_stock():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    producto_id = request.form.get('producto_id', type=int)
    tipo_operacion_id = request.form.get('tipo_operacion_id', type=int)
    concepto_id = request.form.get('concepto_id', type=int)
    origen_id = request.form.get('almacen_origen_id', type=int)
    destino_id = request.form.get('almacen_destino_id', type=int)
    cantidad = request.form.get('cantidad', type=float, default=0.0)

    print(f"DEBUGGING -> producto_id recibido: {producto_id}")
    print(f"DEBUGGING -> origen_id recibido: {origen_id}")
    print(f"DEBUGGING -> cantidad recibida: {cantidad}")

    # Validaciones básicas generales
    if not producto_id or not tipo_operacion_id or not concepto_id or cantidad <= 0:
        flash("Error: Faltan datos obligatorios o la cantidad es inválida.", "danger")
        return redirect(url_for('vista_admin'))

    # Buscar el tipo de operación
    tipo_op = TipoOperacion.query.get(tipo_operacion_id)
    if not tipo_op:
        flash("Error: El tipo de operación seleccionado no es válido.", "danger")
        return redirect(url_for('vista_admin'))

    # Limpiamos y convertimos a minúsculas
    comportamiento = tipo_op.codigo.strip().lower() if tipo_op.codigo else ""

    # Diagnóstico en vivo de los stocks reales en la base de datos para este producto
    stocks_existentes = StockAlmacen.query.filter_by(producto_id=producto_id).all()
    print(f"DEBUGGING -> Pares (almacen_id, cantidad) reales en BD para este producto: {[(s.almacen_id, s.cantidad) for s in stocks_existentes]}")

    # 1. COMPORTAMIENTO: TRASLADO (Origen -> Destino)
    if comportamiento.startswith('traslado'):
        if not origen_id or not destino_id:
            flash("Error: El traslado requiere un almacén de origen y un almacén de destino.", "danger")
            return redirect(url_for('vista_admin'))
        
        if origen_id == destino_id:
            flash("Error: El origen y el destino no pueden ser el mismo almacén.", "danger")
            return redirect(url_for('vista_admin'))
        
        stock_origen = StockAlmacen.query.filter_by(producto_id=producto_id, almacen_id=origen_id).first()
        if not stock_origen or stock_origen.cantidad < cantidad:
            flash("Error: No hay suficiente stock en el almacén de origen para realizar este traslado.", "danger")
            return redirect(url_for('vista_admin'))
        
        stock_origen.cantidad -= cantidad

        stock_destino = StockAlmacen.query.filter_by(producto_id=producto_id, almacen_id=destino_id).first()
        if stock_destino:
            stock_destino.cantidad += cantidad
        else:
            db.session.add(StockAlmacen(producto_id=producto_id, almacen_id=destino_id, cantidad=cantidad))

    # 2. COMPORTAMIENTO: ENTRADA (Solo Destino / Incrementa stock)
    elif comportamiento.startswith('entrada'):
        if not destino_id:
            flash("Error: La entrada requiere seleccionar un almacén de destino.", "danger")
            return redirect(url_for('vista_admin'))
        
        stock_destino = StockAlmacen.query.filter_by(producto_id=producto_id, almacen_id=destino_id).first()
        if stock_destino:
            stock_destino.cantidad += cantidad
        else:
            db.session.add(StockAlmacen(producto_id=producto_id, almacen_id=destino_id, cantidad=cantidad))

    # 3. COMPORTAMIENTO: SALIDA (Solo Origen / Disminuye stock)
    elif comportamiento.startswith('salida'):
        if not origen_id:
            flash("Error: La salida requiere seleccionar un almacén de origen.", "danger")
            return redirect(url_for('vista_admin'))
        
        stock_origen = StockAlmacen.query.filter_by(producto_id=producto_id, almacen_id=origen_id).first()
        if not stock_origen:
            flash("Error: Este producto no tiene registros de stock en el almacén seleccionado.", "danger")
            return redirect(url_for('vista_admin'))
            
        if stock_origen.cantidad < cantidad:
            flash(f"Error: Stock insuficiente. Intentas retirar {cantidad}, pero solo hay {stock_origen.cantidad} disponibles.", "danger")
            return redirect(url_for('vista_admin'))
        
        stock_origen.cantidad -= cantidad

    else:
        flash(f"Error: El código de comportamiento '{tipo_op.codigo}' no está reconocido.", "danger")
        return redirect(url_for('vista_admin'))

    db.session.commit()
    flash("¡Movimiento registrado y stock actualizado con éxito!", "success")
    return redirect(url_for('vista_admin'))
from datetime import datetime

@app.route('/guardar_producto', methods=['POST'])
def guardar_producto():
    # 1. Obtener datos del formulario
    nombre = request.form.get('nombre')
    precio_costo = float(request.form.get('precio_costo', 0))
    precio_venta = float(request.form.get('precio_venta', 0))
    proveedor_id = request.form.get('proveedor_id')  # ID del select de proveedores
    almacen_id = request.form.get('almacen_id')      # ID del select de almacenes
    cantidad_inicial = float(request.form.get('cantidad', 0))
    
    # --- CAPTURAR Y PARSEAR FECHA DE VENCIMIENTO ---
    fecha_venc_str = request.form.get('fecha_vencimiento')
    fecha_vencimiento = None
    if fecha_venc_str:
        try:
            fecha_vencimiento = datetime.strptime(fecha_venc_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_vencimiento = None

    # CAPTURAR EL ESTADO DE PAGO DESDE EL FORMULARIO
    estado_pago = request.form.get('estado_pago', 'Pagado') 
    propietario_id = request.form.get("propietario_id")

    # Si viene como cadena vacía o no existe, puedes definir un valor por defecto o lanzar error
    id_final = int(propietario_id) if propietario_id and propietario_id.isdigit() else None
    # Calcular monto pendiente
    monto_pendiente = 0.0
    if estado_pago == 'Pendiente':
        monto_pendiente = precio_costo * cantidad_inicial

    # 2. Crear el Producto con todos los campos
    nuevo_producto = Producto(
        nombre=nombre,
        precio_costo=precio_costo,
        precio_venta=precio_venta,
        proveedor_id=int(proveedor_id) if proveedor_id else None,
        estado_pago=estado_pago,             
        monto_pendiente=monto_pendiente,
        fecha_vencimiento=fecha_vencimiento,
        propietario_id=id_final
    )
    db.session.add(nuevo_producto)
    db.session.flush()  # Para obtener el ID generado del nuevo_producto

    # 3. Crear el registro en StockAlmacen
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

    username = session.get('user')
    usuario_actual = Usuario.query.filter_by(username=username).first()

    if not usuario_actual or not usuario_actual.almacen_id:
        return jsonify({'success': False, 'message': 'Error: Tu usuario no tiene un almacén asignado.'}), 400

    almacen_usuario_id = usuario_actual.almacen_id

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Datos inválidos'}), 400

    efectivo_caja = float(data.get('efectivo_caja', 0.0))
    total_transferencias = float(data.get('total_transferencias', 0.0))
    productos_cierre = data.get('productos', [])
    deudas_cierre = data.get('deudas', [])

    total_bruto_general = 0.0
    ventas_dayana = 0.0
    tiene_cristian = False

    for p_data in productos_cierre:
        subtotal_prod = float(p_data.get('subtotal', 0.0))
        total_bruto_general += subtotal_prod

        p_id = int(p_data['id'])
        producto_check = Producto.query.get(p_id)
        if producto_check and producto_check.propietario:
            prop_nombre = producto_check.propietario.nombre.lower()
            prop_id = producto_check.propietario.id
            
            if prop_id == 1 or 'dayana' in prop_nombre:
                ventas_dayana += subtotal_prod
            if prop_id == 2 or 'cristian' in prop_nombre:
                tiene_cristian = True

    total_deudas = sum(float(d.get('subtotal', 0.0)) for d in deudas_cierre)

    descuento_cristian = 1000.0 if tiene_cristian else 0.0
    comision_dayana = ventas_dayana * 0.03
    descuento_total = descuento_cristian + comision_dayana

    total_esperado = total_bruto_general - descuento_total - total_transferencias - total_deudas
    diferencia = efectivo_caja - total_esperado

    try:
        nuevo_cierre = CierreDia(
            usuario_id=usuario_actual.id,
            usuario_nombre=usuario_actual.nombre,
            efectivo_caja=efectivo_caja,
            total_transferencias=total_transferencias,
            total_deudas=total_deudas,
            total_esperado=total_esperado,
            diferencia=diferencia
        )
        db.session.add(nuevo_cierre)
        db.session.flush()

        # Guardar detalles de productos vendidos y actualizar stock del almacén
        for p_data in productos_cierre:
            p_id = int(p_data['id'])
            entradas = float(p_data.get('entradas', 0.0))
            stock_final = float(p_data.get('stock_final', 0.0))
            vendidos = float(p_data.get('vendidos', 0.0))
            subtotal = float(p_data.get('subtotal', 0.0))

            producto = Producto.query.get(p_id)
            if producto:
                stock_inicial_calculado = stock_final + vendidos - entradas
                
                detalle = DetalleCierre(
                    cierre_id=nuevo_cierre.id,
                    producto_id=producto.id,
                    nombre_producto=producto.nombre,
                    precio_venta=producto.precio_venta,
                    stock_inicial=stock_inicial_calculado,
                    entradas=entradas,
                    stock_final=stock_final,
                    vendidos=vendidos,
                    subtotal=subtotal
                )
                db.session.add(detalle)

                # Actualizar inventario físico en el almacén del usuario
                stock_almacen = StockAlmacen.query.filter_by(
                    producto_id=producto.id, 
                    almacen_id=almacen_usuario_id
                ).first()
                
                if stock_almacen:
                    stock_almacen.cantidad = stock_final
                else:
                    nuevo_stock = StockAlmacen(
                        producto_id=producto.id,
                        almacen_id=almacen_usuario_id,
                        cantidad=stock_final
                    )
                    db.session.add(nuevo_stock)

        # Guardar deudas asociadas al cierre
        for d_data in deudas_cierre:
            deuda = DeudaCierre(
                cierre_id=nuevo_cierre.id,
                producto_id=int(d_data.get('producto_id', 0)),
                producto_nombre=d_data.get('producto_nombre', ''),
                concepto=d_data.get('concepto', ''),
                cantidad=float(d_data.get('cantidad', 0.0)),
                subtotal=float(d_data.get('subtotal', 0.0))
            )
            db.session.add(deuda)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Cierre procesado correctamente'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    
@app.route('/editar_producto/<int:id>', methods=['POST'])
def editar_producto(id):
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    producto = Producto.query.get_or_404(id)

    # 1. Obtener datos del formulario
    producto.nombre = request.form.get('nombre')
    producto.unidad_medida = request.form.get('unidad_medida', 'u')
    producto.precio_costo = float(request.form.get('precio_costo', 0.0))
    producto.precio_venta = float(request.form.get('precio_venta', 0.0))
    
    proveedor_id = request.form.get('proveedor_id')
    producto.proveedor_id = int(proveedor_id) if proveedor_id else None
    
    propietario_id = request.form.get('propietario_id')
    producto.propietario_id = int(propietario_id) if propietario_id else None


    # Parsear Fecha de Vencimiento
    fecha_venc_str = request.form.get('fecha_vencimiento')
    if fecha_venc_str:
        try:
            producto.fecha_vencimiento = datetime.strptime(fecha_venc_str, '%Y-%m-%d').date()
        except ValueError:
            producto.fecha_vencimiento = None
    else:
        producto.fecha_vencimiento = None

    db.session.commit()
    flash("Producto actualizado exitosamente", "info")
    return redirect(url_for('vista_admin'))    
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
    
    ganancias_por_propietario = {}
    ventas_brutas_por_propietario = {}
    descuentos_por_propietario = {}  # <-- Para almacenar las deducciones explicadas

    for d in cierre.detalles:
        producto = Producto.query.get(d.producto_id)
        precio_costo = producto.precio_costo if producto else 0.0
        
        propietario_nombre = "Sin Propietario"
        if producto and producto.propietario:
            propietario_nombre = producto.propietario.nombre

        ganancia_item = d.vendidos * (d.precio_venta - precio_costo)
        venta_bruta_item = d.subtotal

        if propietario_nombre not in ganancias_por_propietario:
            ganancias_por_propietario[propietario_nombre] = 0.0
            descuentos_por_propietario[propietario_nombre] = {"tipo": None, "monto": 0.0}
            
        ganancias_por_propietario[propietario_nombre] += ganancia_item

        if propietario_nombre not in ventas_brutas_por_propietario:
            ventas_brutas_por_propietario[propietario_nombre] = 0.0
        ventas_brutas_por_propietario[propietario_nombre] += venta_bruta_item

        detalles.append({
            'nombre_producto': d.nombre_producto,
            'precio_venta': d.precio_venta,
            'stock_inicial': d.stock_inicial,
            'entradas': d.entradas,
            'stock_final': d.stock_final,
            'vendidos': d.vendidos,
            'subtotal': d.subtotal
        })

    # APLICAR DESCUENTOS ESPECÍFICOS Y REGISTRARLOS
    for propietario_nombre in ganancias_por_propietario:
        nombre_lower = propietario_nombre.strip().lower()
        
        if "cristian" in nombre_lower:
            descuento = 1000.0
            ganancias_por_propietario[propietario_nombre] -= descuento
            descuentos_por_propietario[propietario_nombre] = {
                "label": "Salario", 
                "monto": descuento
            }
            
        elif "dayana" in nombre_lower:
            venta_dayana = ventas_brutas_por_propietario.get(propietario_nombre, 0.0)
            descuento = venta_dayana * 0.03
            ganancias_por_propietario[propietario_nombre] -= descuento
            descuentos_por_propietario[propietario_nombre] = {
                "label": "Comisión 3%", 
                "monto": descuento
            }

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
        'detalles': detalles,
        'ganancias_propietarios': ganancias_por_propietario,
        'ventas_brutas_propietarios': ventas_brutas_por_propietario,
        'descuentos_propietarios': descuentos_por_propietario  # <-- Enviamos los detalles de las deducciones
    })
# -----------------------------------------------------------------#
# CUENTAS POR PAGAR
# -----------------------------------------------------------------#

import urllib.parse

@app.route('/admin/cuentas-por-pagar')
@app.route('/cuentas-por-pagar')
def cuentas_por_pagar():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    proveedor_filtro = request.args.get('proveedor', '')

    todos_los_proveedores = Proveedor.query.all()
    query = Producto.query.filter_by(estado_pago='Pendiente')

    proveedor_obj = None
    if proveedor_filtro and proveedor_filtro.isdigit():
        query = query.filter_by(proveedor_id=int(proveedor_filtro))
        proveedor_obj = Proveedor.query.get(int(proveedor_filtro))

    cuentas_pendientes = query.all()
    total_adeudado = sum(item.monto_pendiente for item in cuentas_pendientes if item.monto_pendiente)

    # Cargar los últimos 20 pagos del historial
    historial = HistorialPago.query.order_by(HistorialPago.fecha_pago.desc()).limit(20).all()

    # Generar el mensaje de WhatsApp si hay un proveedor seleccionado
    mensaje_wa = ""
    if proveedor_obj and cuentas_pendientes:
        lineas = [f"*RESUMEN DE CUENTA PENDIENTE*", f"*Proveedor:* {proveedor_obj.nombre}\n"]
        for p in cuentas_pendientes:
            cant = p.cantidad_total or 0
            lineas.append(f"• {p.nombre} ({cant} unid.) -> *${'%.2f' % p.monto_pendiente}*")
        
        lineas.append(f"\n*TOTAL ADEUDADO:* *${'%.2f' % total_adeudado}*")
        lineas.append(" Quedo al pendiente para realizar el pago. ¡Gracias!")
        
        texto_completo = "\n".join(lineas)
        mensaje_wa = urllib.parse.quote(texto_completo)

    return render_template(
        'cuentas_por_pagar.html',
        cuentas=cuentas_pendientes,
        proveedores=todos_los_proveedores,
        proveedor_seleccionado=str(proveedor_filtro),
        proveedor_obj=proveedor_obj,
        total_adeudado=total_adeudado,
        historial=historial,
        mensaje_wa=mensaje_wa
    )

# -----------------------------------------------------------------#
# GESTIÓN DE USUARIOS
# -----------------------------------------------------------------#

@app.route('/admin/usuarios')
def vista_usuarios():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
    
    usuarios = Usuario.query.all()
    almacenes = Almacen.query.all()
    return render_template('admin_usuarios.html', usuarios=usuarios, almacenes=almacenes)


@app.route('/admin/usuarios/nuevo', methods=['POST'])
def guardar_usuario():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    username = request.form.get('username')
    nombre = request.form.get('nombre')
    password = request.form.get('password')
    rol = request.form.get('rol')
    
    # Capturamos el almacén seleccionado en el formulario (si viene vacío o no seleccionado, será None)
    almacen_id = request.form.get('almacen_id')

    if Usuario.query.filter_by(username=username).first():
        flash("El nombre de usuario ya existe.", "error")
        return redirect(url_for('vista_usuarios'))

    nuevo_user = Usuario(
        username=username,
        nombre=nombre,
        password=password,
        rol=rol,
        almacen_id=almacen_id if almacen_id else None  # Asignamos el almacén correspondiente
    )

    db.session.add(nuevo_user)
    db.session.commit()

    flash("Usuario creado y vinculado al almacén exitosamente.", "success")
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
    