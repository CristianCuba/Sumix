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
# ==========================================
# MODELOS PARA MÓDULO BALANCE Y PATRIMONIO
# ==========================================

class PrestamoTercero(db.Model):
    """Registro de dinero del negocio prestado a personas externas."""
    __tablename__ = 'prestamos_terceros'
    id = db.Column(db.Integer, primary_key=True)
    propietario_id = db.Column(db.Integer, db.ForeignKey('propietarios.id'), nullable=False)
    deudor_nombre = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    saldo_pendiente = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(20), default='EFECTIVO')  # 'EFECTIVO' o 'TRANSFERENCIA'
    concepto = db.Column(db.String(255), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.now)
    estado = db.Column(db.String(20), default='PENDIENTE')

    propietario = db.relationship('Propietario', backref=db.backref('prestamos', lazy=True))
class CuentaPorPagar(db.Model):
    __tablename__ = 'cuentas_por_pagar'
    id = db.Column(db.Integer, primary_key=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'))  # Revisa el nombre de tu tabla de proveedores
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'))      # Revisa el nombre de tu tabla de productos
    cantidad = db.Column(db.Integer, default=1)
    monto_total = db.Column(db.Float, nullable=False)
    monto_pendiente = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='pendiente')

    # AGREGA ESTAS DOS LÍNEAS AL FINAL DEL MODELO:
    proveedor = db.relationship('Proveedor', backref='cuentas_por_pagar')
    producto = db.relationship('Producto', backref='cuentas_por_pagar')

class MovimientoCapital(db.Model):
    """Inyecciones o Retiros de dinero realizados por los propietarios."""
    __tablename__ = 'movimientos_capital'
    id = db.Column(db.Integer, primary_key=True)
    propietario_id = db.Column(db.Integer, db.ForeignKey('propietarios.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False) # 'INYECCION' o 'RETIRO'
    monto = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(20), default='EFECTIVO') # 'EFECTIVO' o 'TRANSFERENCIA'
    concepto = db.Column(db.String(255), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.now)

    propietario = db.relationship('Propietario', backref=db.backref('movimientos_capital', lazy=True))


class SnapshotBalanceDiario(db.Model):
    """Registro histórico del balance patrimonio al cierre del día."""
    __tablename__ = 'snapshots_balance_diario'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    propietario_nombre = db.Column(db.String(100), nullable=False)
    efectivo = db.Column(db.Float, default=0.0)
    transferencia = db.Column(db.Float, default=0.0)
    inventario_costo = db.Column(db.Float, default=0.0)
    deudas_por_cobrar = db.Column(db.Float, default=0.0)
    prestamos_otorgados = db.Column(db.Float, default=0.0)
    inyecciones = db.Column(db.Float, default=0.0)
    retiros = db.Column(db.Float, default=0.0)
    patrimonio_total = db.Column(db.Float, default=0.0)

class Compra(db.Model):
    __tablename__ = 'compra'
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.now)
    efectivo_inicial = db.Column(db.Float, default=0.0)
    total_compra = db.Column(db.Float, default=0.0)
    efectivo_restante = db.Column(db.Float, default=0.0)
    
    # ⚠️ CAMPOS NUEVOS (Añadir estos dos):
    propietario_id = db.Column(db.Integer, db.ForeignKey('propietarios.id'), nullable=True)
    metodo_pago = db.Column(db.String(20), default='EFECTIVO')

    items = db.relationship('ItemCompra', backref='compra', lazy=True)
    propietario = db.relationship('Propietario', backref='compras')

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
    
    # Relación con Proveedor
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=True)
    proveedor = db.relationship('Proveedor', backref=db.backref('productos', lazy=True))
    
    # Cuentas por Pagar
    estado_pago = db.Column(db.String(20), default="Pagado")
    monto_pendiente = db.Column(db.Float, default=0.0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # --- CAMPO NUEVO PARA BORRADO LÓGICO ---
    activo = db.Column(db.Boolean, default=True)

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
    total_deudas = db.Column(db.Float, default=0.0)
    diferencia = db.Column(db.Float, default=0.0)
    observaciones = db.Column(db.Text, nullable=True)  # <-- NUEVO CAMPO
    detalles = db.relationship('DetalleCierre', backref='cierre', lazy=True)
    deudas = db.relationship('DeudaCierre', backref='cierre', lazy=True)
    usuario = db.relationship('Usuario', backref='cierres_dia')


class DeudaCierre(db.Model):
    __tablename__ = 'deudas_cierre'
    id = db.Column(db.Integer, primary_key=True)
    cierre_id = db.Column(db.Integer, db.ForeignKey('cierres_dia.id'), nullable=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=True)
    producto_nombre = db.Column(db.String(100), nullable=True)
    concepto = db.Column(db.String(150), nullable=False)
    cantidad = db.Column(db.Float, default=1.0)
    subtotal = db.Column(db.Float, default=0.0)
    estado = db.Column(db.String(20), default='pendiente')
    fecha = db.Column(db.DateTime, default=datetime.now)
    producto = db.relationship('Producto', backref='deudas_cierre')


class DetalleCierre(db.Model):
    __tablename__ = 'detalles_cierre'
    
    id = db.Column(db.Integer, primary_key=True)
    cierre_id = db.Column(db.Integer, db.ForeignKey('cierres_dia.id'), nullable=False)
    
    # Se cambia a nullable=True para que no falle el historial si en el futuro se desactiva un producto
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=True)
    
    nombre_producto = db.Column(db.String(100), nullable=False)
    propietario_nombre = db.Column(db.String(100), nullable=True)
    
    # --- CAMPOS HISTÓRICOS (SNAPSHOT) ---
    precio_costo = db.Column(db.Float, default=0.0)        # Congela el costo unitario del día de la venta
    propietario_id = db.Column(db.Integer, nullable=True)  # Congela el ID del propietario
    proveedor_id = db.Column(db.Integer, nullable=True)    # Congela el ID del proveedor
    
    # Datos de cantidades y montos del cierre
    precio_venta = db.Column(db.Float, default=0.0)
    stock_inicial = db.Column(db.Float, default=0.0)
    entradas = db.Column(db.Float, default=0.0)
    stock_final = db.Column(db.Float, default=0.0)
    vendidos = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, default=0.0)
    
    # Relación ORM
    producto = db.relationship('Producto', backref='detalles_cierre')

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
from datetime import datetime, date

# ==========================================
# RUTAS PARA EL MÓDULO DE BALANCE Y PATRIMONIO
# ==========================================

def obtener_stock_total(producto):
    """Calcula el stock total de un producto considerando si 'stocks' es una lista/relación o un valor entero."""
    if hasattr(producto, 'stocks'):
        if isinstance(producto.stocks, (list, tuple)) or hasattr(producto.stocks, '__iter__'):
            return sum(getattr(s, 'cantidad', getattr(s, 'stock', 0)) for s in producto.stocks)
        return producto.stocks or 0
    return getattr(producto, 'stock', 0)


@app.route('/admin/balance')
def vista_balance():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    propietarios = Propietario.query.all()
    balance_propietarios = []

    for prop in propietarios:
        # 1. Capital Invertido en Mercado/Productos (Valor a Costo)
        productos_prop = Producto.query.filter_by(propietario_id=prop.id).all()
        inventario_costo = sum((obtener_stock_total(p) * (p.precio_costo or 0.0)) for p in productos_prop)

        # 2. Deudas por Cobrar (Consulta SQL directa a deudas_cierre)
        deudas_cobrar = 0.0
        try:
            filas_deudas = db.session.execute(
                db.text("SELECT * FROM deudas_cierre WHERE LOWER(COALESCE(estado, '')) = 'pendiente' OR cierre_pago_id IS NULL")
            ).mappings().all()

            for row in filas_deudas:
                # Omitir deudas pagadas o canceladas
                estado_str = str(row.get('estado', '')).lower()
                if estado_str == 'pagado' or row.get('cierre_pago_id') is not None:
                    continue

                monto_d = float(row.get('subtotal') or 0.0)
                if monto_d <= 0:
                    continue

                prod_id = row.get('producto_id')
                prod_nom = str(row.get('producto_nombre') or '').strip()

                prod = None
                if prod_id and prod_id > 0:
                    prod = Producto.query.get(prod_id)
                elif prod_nom:
                    prod = Producto.query.filter(Producto.nombre.ilike(prod_nom)).first()

                # Si el producto tiene socio, se le asigna a él. Si es concepto general, se asigna a Cristian.
                if prod and prod.propietario_id == prop.id:
                    deudas_cobrar += monto_d
                elif not prod and 'CRISTIAN' in prop.nombre.upper():
                    deudas_cobrar += monto_d
        except Exception:
            deudas_cobrar = 0.0

        # 3. Préstamos Otorgados a terceros
        prestamos = PrestamoTercero.query.filter_by(propietario_id=prop.id, estado='PENDIENTE').all()
        prestamos_efectivo = sum(p.saldo_pendiente for p in prestamos if not getattr(p, 'metodo_pago', None) or p.metodo_pago == 'EFECTIVO')
        prestamos_transf = sum(p.saldo_pendiente for p in prestamos if getattr(p, 'metodo_pago', None) == 'TRANSFERENCIA')
        total_prestamos = prestamos_efectivo + prestamos_transf

        # 4. Movimientos de Capital (Inyecciones / Retiros)
        movs = MovimientoCapital.query.filter_by(propietario_id=prop.id).all()

        inyecciones_efectivo = sum(m.monto for m in movs if m.tipo == 'INYECCION' and (not getattr(m, 'metodo_pago', None) or m.metodo_pago == 'EFECTIVO'))
        retiros_efectivo = sum(m.monto for m in movs if m.tipo == 'RETIRO' and (not getattr(m, 'metodo_pago', None) or m.metodo_pago == 'EFECTIVO'))

        inyecciones_transf = sum(m.monto for m in movs if m.tipo == 'INYECCION' and getattr(m, 'metodo_pago', None) == 'TRANSFERENCIA')
        retiros_transf = sum(m.monto for m in movs if m.tipo == 'RETIRO' and getattr(m, 'metodo_pago', None) == 'TRANSFERENCIA')

        total_inyecciones = inyecciones_efectivo + inyecciones_transf
        total_retiros = retiros_efectivo + retiros_transf

        # 5. Compras realizadas por este socio
        compras_socio = Compra.query.filter_by(propietario_id=prop.id).all() if 'Compra' in globals() else []
        compras_efectivo = sum(c.total_compra for c in compras_socio if c.metodo_pago == 'EFECTIVO' or not c.metodo_pago)
        compras_transf = sum(c.total_compra for c in compras_socio if c.metodo_pago == 'TRANSFERENCIA')

        # 6. Cierres de Venta y Transferencias acumuladas
        efectivo_acumulado = 0.0
        transferencias_cierres = 0.0
        es_cristian = 'CRISTIAN' in prop.nombre.upper()

        if 'CierreDia' in globals():
            cierres = CierreDia.query.all()
            for c in cierres:
                if hasattr(c, 'detalles'):
                    for d in c.detalles:
                        prod = Producto.query.get(d.producto_id)
                        if prod and prod.propietario_id == prop.id:
                            efectivo_acumulado += (d.subtotal or 0.0)

                if es_cristian and hasattr(c, 'total_transferencias') and c.total_transferencias:
                    transferencias_cierres += (c.total_transferencias or 0.0)

        # Totales líquidos desglosados
        efectivo_liquido = max(0.0, efectivo_acumulado + inyecciones_efectivo - retiros_efectivo - prestamos_efectivo - compras_efectivo)
        transferencias_acumuladas = max(0.0, transferencias_cierres + inyecciones_transf - retiros_transf - prestamos_transf - compras_transf)

        # Patrimonio Neto Total (incluye Deudas por Cobrar)
        patrimonio_total = efectivo_liquido + transferencias_acumuladas + inventario_costo + deudas_cobrar + total_prestamos

        balance_propietarios.append({
            'propietario': prop,
            'efectivo': efectivo_liquido,
            'transferencia': transferencias_acumuladas,
            'inventario_costo': inventario_costo,
            'deudas_por_cobrar': deudas_cobrar,
            'prestamos': total_prestamos,
            'inyecciones': total_inyecciones,
            'retiros': total_retiros,
            'patrimonio_total': patrimonio_total
        })

    snapshots = SnapshotBalanceDiario.query.order_by(SnapshotBalanceDiario.fecha.desc()).limit(30).all()
    prestamos_activos = PrestamoTercero.query.filter_by(estado='PENDIENTE').all()

    return render_template(
        'admin_balance.html',
        balance_propietarios=balance_propietarios,
        snapshots=snapshots,
        prestamos=prestamos_activos,
        propietarios=propietarios
    )


@app.route('/admin/balance/guardar-snapshot', methods=['POST'])
def guardar_snapshot_diario():
    if 'user' not in session or session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'}), 403

    try:
        hoy = date.today()
        propietarios = Propietario.query.all()

        for prop in propietarios:
            SnapshotBalanceDiario.query.filter_by(fecha=hoy, propietario_nombre=prop.nombre).delete()

            productos_prop = Producto.query.filter_by(propietario_id=prop.id).all()
            inventario_costo = sum((obtener_stock_total(p) * (p.precio_costo or 0.0)) for p in productos_prop)

            # 2. Deudas por Cobrar (Consulta SQL directa a deudas_cierre)
            deudas_cobrar = 0.0
            try:
                filas_deudas = db.session.execute(
                    db.text("SELECT * FROM deudas_cierre WHERE LOWER(COALESCE(estado, '')) = 'pendiente' OR cierre_pago_id IS NULL")
                ).mappings().all()

                for row in filas_deudas:
                    estado_str = str(row.get('estado', '')).lower()
                    if estado_str == 'pagado' or row.get('cierre_pago_id') is not None:
                        continue

                    monto_d = float(row.get('subtotal') or 0.0)
                    if monto_d <= 0:
                        continue

                    prod_id = row.get('producto_id')
                    prod_nom = str(row.get('producto_nombre') or '').strip()

                    prod = None
                    if prod_id and prod_id > 0:
                        prod = Producto.query.get(prod_id)
                    elif prod_nom:
                        prod = Producto.query.filter(Producto.nombre.ilike(prod_nom)).first()

                    if prod and prod.propietario_id == prop.id:
                        deudas_cobrar += monto_d
                    elif not prod and 'CRISTIAN' in prop.nombre.upper():
                        deudas_cobrar += monto_d
            except Exception:
                deudas_cobrar = 0.0

            prestamos = PrestamoTercero.query.filter_by(propietario_id=prop.id, estado='PENDIENTE').all()
            prestamos_efectivo = sum(p.saldo_pendiente for p in prestamos if not getattr(p, 'metodo_pago', None) or p.metodo_pago == 'EFECTIVO')
            prestamos_transf = sum(p.saldo_pendiente for p in prestamos if getattr(p, 'metodo_pago', None) == 'TRANSFERENCIA')
            total_prestamos = prestamos_efectivo + prestamos_transf

            movs = MovimientoCapital.query.filter_by(propietario_id=prop.id).all()

            inyecciones_efectivo = sum(m.monto for m in movs if m.tipo == 'INYECCION' and (not getattr(m, 'metodo_pago', None) or m.metodo_pago == 'EFECTIVO'))
            retiros_efectivo = sum(m.monto for m in movs if m.tipo == 'RETIRO' and (not getattr(m, 'metodo_pago', None) or m.metodo_pago == 'EFECTIVO'))

            inyecciones_transf = sum(m.monto for m in movs if m.tipo == 'INYECCION' and getattr(m, 'metodo_pago', None) == 'TRANSFERENCIA')
            retiros_transf = sum(m.monto for m in movs if m.tipo == 'RETIRO' and getattr(m, 'metodo_pago', None) == 'TRANSFERENCIA')

            total_inyecciones = inyecciones_efectivo + inyecciones_transf
            total_retiros = retiros_efectivo + retiros_transf

            compras_socio = Compra.query.filter_by(propietario_id=prop.id).all() if 'Compra' in globals() else []
            compras_efectivo = sum(c.total_compra for c in compras_socio if c.metodo_pago == 'EFECTIVO' or not c.metodo_pago)
            compras_transf = sum(c.total_compra for c in compras_socio if c.metodo_pago == 'TRANSFERENCIA')

            efectivo_acumulado = 0.0
            transferencias_cierres = 0.0
            es_cristian = 'CRISTIAN' in prop.nombre.upper()

            if 'CierreDia' in globals():
                cierres = CierreDia.query.all()
                for c in cierres:
                    if hasattr(c, 'detalles'):
                        for d in c.detalles:
                            prod = Producto.query.get(d.producto_id)
                            if prod and prod.propietario_id == prop.id:
                                efectivo_acumulado += (d.subtotal or 0.0)

                    if es_cristian and hasattr(c, 'total_transferencias') and c.total_transferencias:
                        transferencias_cierres += (c.total_transferencias or 0.0)

            efectivo_liquido = max(0.0, efectivo_acumulado + inyecciones_efectivo - retiros_efectivo - prestamos_efectivo - compras_efectivo)
            transferencias_acumuladas = max(0.0, transferencias_cierres + inyecciones_transf - retiros_transf - prestamos_transf - compras_transf)

            patrimonio_total = efectivo_liquido + transferencias_acumuladas + inventario_costo + deudas_cobrar + total_prestamos

            snap = SnapshotBalanceDiario(
                fecha=hoy,
                propietario_nombre=prop.nombre,
                efectivo=efectivo_liquido,
                transferencia=transferencias_acumuladas,
                inventario_costo=inventario_costo,
                deudas_por_cobrar=deudas_cobrar,
                prestamos_otorgados=total_prestamos,
                inyecciones=total_inyecciones,
                retiros=total_retiros,
                patrimonio_total=patrimonio_total
            )
            db.session.add(snap)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Snapshot congelado en el historial.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
        
@app.route('/admin/balance/movimiento', methods=['POST'])
def registrar_movimiento_capital():
    if 'user' not in session or session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'}), 403

    data = request.json or {}
    try:
        nuevo_mov = MovimientoCapital(
            propietario_id=int(data['propietario_id']),
            tipo=data['tipo'],  # 'INYECCION' o 'RETIRO'
            monto=float(data['monto']),
            metodo_pago=data.get('metodo_pago', 'EFECTIVO'),
            concepto=data.get('concepto', '')
        )
        db.session.add(nuevo_mov)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Movimiento registrado correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/admin/balance/prestamo', methods=['POST'])
def registrar_prestamo():
    if 'user' not in session or session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'}), 403

    data = request.json or {}
    try:
        nuevo_prestamo = PrestamoTercero(
            propietario_id=int(data['propietario_id']),
            deudor_nombre=data['deudor_nombre'],
            monto=float(data['monto']),
            saldo_pendiente=float(data['monto']),
            metodo_pago=data.get('metodo_pago', 'EFECTIVO'),
            concepto=data.get('concepto', '')
        )
        db.session.add(nuevo_prestamo)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Préstamo registrado correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

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
# -----------------------------------------------------------------#
# RUTAS DE DEUDAS Y FIADOS (ACCESIBLE PARA DEPENDIENTES Y ADMINS)
# -----------------------------------------------------------------#
@app.route('/deudas')
def vista_deudas():
    if 'user' not in session:
        return redirect(url_for('login'))

    productos = Producto.query.all()
    deudas_pendientes = DeudaCierre.query.filter_by(estado='pendiente').order_by(DeudaCierre.id.desc()).all()
    deudas_cobradas = DeudaCierre.query.filter_by(estado='pagado').order_by(DeudaCierre.id.desc()).limit(20).all()
    
    total_pendiente = sum(d.subtotal for d in deudas_pendientes if d.subtotal)

    return render_template(
        'deudas.html', 
        productos=productos, 
        deudas=deudas_pendientes, 
        historial=deudas_cobradas,
        total_pendiente=total_pendiente
    )

@app.route('/api/deudas-dia-total', methods=['GET'])
def api_deudas_dia_total():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    hoy = date.today()
    deudas_pendientes = DeudaCierre.query.filter(
        DeudaCierre.estado == 'pendiente',
        func.date(DeudaCierre.fecha) == hoy
    ).all()
    
    total_deudas_dia = sum(d.subtotal for d in deudas_pendientes if d.subtotal)
    return jsonify({'success': True, 'total': total_deudas_dia})

@app.route('/deudas/nueva', methods=['POST'])
def guardar_deuda():
    if 'user' not in session:
        return redirect(url_for('login'))

    concepto = request.form.get('concepto', '').strip()
    producto_id = request.form.get('producto_id', type=int)
    cantidad = request.form.get('cantidad', type=float, default=1.0)
    
    # NUEVO: Capturar la fecha que viene del formulario
    fecha_recibida = request.form.get('fecha')

    if not concepto or cantidad <= 0:
        flash("Ingresa un concepto/deudor válido.", "danger")
        return redirect(url_for('vista_deudas'))

    prod_nombre = ""
    subtotal = 0.0

    if producto_id:
        prod = Producto.query.get(producto_id)
        if prod:
            prod_nombre = prod.nombre
            subtotal = cantidad * prod.precio_venta

    # NUEVO: Convertir la fecha de texto a objeto datetime
    if fecha_recibida:
        fecha_obj = datetime.strptime(fecha_recibida, '%Y-%m-%d')
    else:
        fecha_obj = datetime.now()

    nueva_deuda = DeudaCierre(
        concepto=concepto,
        producto_id=producto_id if producto_id else 0,
        producto_nombre=prod_nombre,
        cantidad=cantidad,
        subtotal=subtotal,
        estado='pendiente',
        fecha=fecha_obj  # NUEVO: Guardar la fecha en la base de datos
    )

    db.session.add(nueva_deuda)
    db.session.commit()
    flash("Deuda / Fiado registrado correctamente.", "success")
    return redirect(url_for('vista_deudas'))


@app.route('/deudas/cobrar/<int:id>', methods=['POST'])
def cobrar_deuda(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    deuda = DeudaCierre.query.get_or_404(id)
    deuda.estado = 'pagado'

    db.session.commit()
    flash(f"Deuda de '{deuda.concepto}' marcada como cobrada.", "success")
    return redirect(url_for('vista_deudas'))

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

from datetime import date
from sqlalchemy import func

@app.route('/cierre')
def vista_cierre():
    # 1. Validación del usuario y obtención de su almacén
    username = session.get('user')
    usuario_actual = Usuario.query.filter_by(username=username).first()
    
    if not usuario_actual:
        return redirect(url_for('login'))

    almacen_id = usuario_actual.almacen_id
    
    # 2. Carga ÚNICAMENTE de productos activos para la caja diaria (Borrado Lógico)
    productos = Producto.query.filter(or_(Producto.activo == True, Producto.activo.is_(None))).all()
    
    for prod in productos:
        stock_alm = StockAlmacen.query.filter_by(
            producto_id=prod.id, 
            almacen_id=almacen_id
        ).first()
        
        cantidad_actual = stock_alm.cantidad if stock_alm else 0.0
        
        prod.stock_en_almacen = cantidad_actual
        prod.stock_final_inicial = cantidad_actual

    # 3. ORDENAMIENTO DE PRODUCTOS:
    # - Primero los productos con stock > 0 (ordenados alfabéticamente)
    # - Al final los productos con stock == 0 (ordenados alfabéticamente)
    productos.sort(key=lambda p: (p.stock_en_almacen <= 0, p.nombre.lower()))

    # 4. Cálculo de deudas pendientes exclusivas de HOY
    hoy = date.today()
    deudas_pendientes = DeudaCierre.query.filter(
        DeudaCierre.estado == 'pendiente',
        func.date(DeudaCierre.fecha) == hoy
    ).all()
    
    total_deudas_dia = sum(d.subtotal for d in deudas_pendientes if d.subtotal)

    # 5. Renderizar la plantilla enviando los productos ordenados y el total de deudas
    return render_template('cierre.html', productos=productos, total_deudas_dia=total_deudas_dia)

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

    # Conversión limpia de conceptos a JSON para JavaScript
    conceptos_json = [
        {"id": c.id, "tipo_id": c.tipo_id, "nombre": c.nombre} 
        for c in conceptos
    ]

    # 2. Captura del filtro de propietario desde la URL
    propietario_filtro_id = request.args.get("propietario_id", "todos")

    # 3. Consulta de productos ACTIVOS únicamente (Borrado Lógico)
    query_activos = Producto.query.filter(or_(Producto.activo == True, Producto.activo.is_(None)))

    if propietario_filtro_id != "todos" and propietario_filtro_id.isdigit():
        productos = query_activos.filter_by(
            propietario_id=int(propietario_filtro_id)
        ).all()
    else:
        productos = query_activos.all()

    # 4. ORDENAMIENTO DE PRODUCTOS EN ADMINISTRACIÓN:
    # - Primero los productos con existencia total > 0 (ordenados alfabéticamente)
    # - Al final los productos con existencia total == 0 (ordenados alfabéticamente)
    productos.sort(key=lambda p: (p.cantidad_total <= 0, p.nombre.lower()))

    # 5. Cálculo de métricas usando las propiedades del modelo Producto
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

    # 6. Renderizado alineado exactamente con la plantilla Jinja2
    return render_template(
        "admin_almacenes.html",
        almacenes=almacenes,
        proveedores=proveedores,
        propietarios=propietarios,
        tipos_operacion=tipos_operacion,
        conceptos=conceptos,
        conceptos_json=conceptos_json,
        productos=productos,
        propietario_filtro_id=str(propietario_filtro_id),
        total_invertido=inversion_stock,
        total_venta_estimada=valor_venta,
        ganancia_potencial=ganancia_proyectada,
        efectivo_caja=efectivo_caja,
        hoy=date.today(),
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

from datetime import datetime

@app.route('/guardar_producto', methods=['POST'])
def guardar_producto():
    try:
        # 1. Obtener y limpiar los datos enviados desde el Modal HTML
        nombre = request.form.get('nombre')
        almacen_id = request.form.get('almacen_id', type=int)
        cantidad = float(request.form.get('cantidad', 0))
        unidad_medida = request.form.get('unidad_medida', 'u')
        precio_costo = float(request.form.get('precio_costo', 0))
        precio_venta = float(request.form.get('precio_venta', 0))
        estado_pago = request.form.get('estado_pago')  # 'Pagado' o 'Pendiente'
        
        # Parseo seguro de relaciones opcionales (IDs)
        proveedor_id = int(request.form.get('proveedor_id')) if request.form.get('proveedor_id') else None
        propietario_id = int(request.form.get('propietario_id')) if request.form.get('propietario_id') else None
        
        # Parseo de fecha de vencimiento
        fecha_venc_raw = request.form.get('fecha_vencimiento')
        fecha_vencimiento = datetime.strptime(fecha_venc_raw, '%Y-%m-%d').date() if fecha_venc_raw else None

        # 2. Crear el registro del Producto
        nuevo_producto = Producto(
            nombre=nombre,
            unidad_medida=unidad_medida,
            precio_costo=precio_costo,
            precio_venta=precio_venta,
            proveedor_id=proveedor_id,
            propietario_id=propietario_id,
            fecha_vencimiento=fecha_vencimiento
        )
        db.session.add(nuevo_producto)
        db.session.flush()  # Genera el ID de nuevo_producto sin cerrar la transacción

        # 3. Asignar el stock inicial al Almacén seleccionado
        if almacen_id and cantidad > 0:
            nuevo_stock = StockAlmacen(
                almacen_id=almacen_id,
                producto_id=nuevo_producto.id,
                cantidad=cantidad
            )
            db.session.add(nuevo_stock)

        # 4. Generar la Cuenta por Pagar SI EL PAGO ES PENDIENTE
        if estado_pago == 'Pendiente' and proveedor_id:
            monto_deuda = precio_costo * cantidad
            
            nueva_cuenta = CuentaPorPagar(
                proveedor_id=proveedor_id,
                producto_id=nuevo_producto.id,
                monto_total=monto_deuda,
                monto_pendiente=monto_deuda,
                fecha=datetime.now(),
                estado='pendiente'
            )
            db.session.add(nueva_cuenta)

        db.session.commit()
        flash("Producto registrado con éxito y cuenta por pagar asociada.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar el producto: {str(e)}", "danger")

    return redirect(url_for('vista_admin'))

@app.route('/eliminar_producto/<int:id>', methods=['POST'])
def eliminar_producto(id):
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    producto = Producto.query.get_or_404(id)
    
    # Borrado Lógico: Se marca como inactivo
    producto.activo = False
    db.session.commit()

    flash(f"El producto '{producto.nombre}' ha sido retirado del inventario activo.", "info")
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
    observaciones = data.get('observaciones', '').strip()  # <--- NUEVO: Capturar observaciones
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
            diferencia=diferencia,
            observaciones=observaciones  # <--- NUEVO: Guardar observaciones en la base de datos
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
                prop_nombre = producto.propietario.nombre if producto.propietario else "Sin Propietario"
                
                # --- AQUÍ SE CONGELAN LOS DATOS HISTÓRICOS ---
                detalle = DetalleCierre(
                    cierre_id=nuevo_cierre.id,
                    producto_id=producto.id,
                    nombre_producto=producto.nombre,
                    propietario_nombre=prop_nombre,
                    
                    # Nuevos campos del snapshot:
                    precio_costo=producto.precio_costo or 0.0,   # Congela el costo unitario de hoy
                    propietario_id=producto.propietario_id,     # Congela ID del socio
                    proveedor_id=producto.proveedor_id,         # Congela ID del proveedor
                    
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

from datetime import datetime
from flask import request

from datetime import datetime
from flask import request, session, redirect, url_for, render_template

from sqlalchemy import or_

@app.route('/admin/cierres')
def vista_reporte_cierres():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    fecha_inicio_str = request.args.get('fecha_inicio')
    fecha_fin_str = request.args.get('fecha_fin')
    propietario_id = request.args.get('propietario_id')
    proveedor_id = request.args.get('proveedor_id')

    query = CierreDia.query

    # 1. Filtro en Base de Datos adaptado para soportar historial congelado
    if propietario_id or proveedor_id:
        query = query.join(DetalleCierre)
        if propietario_id:
            query = query.filter(
                or_(
                    DetalleCierre.propietario_id == int(propietario_id),
                    DetalleCierre.producto.has(Producto.propietario_id == int(propietario_id))
                )
            )
        if proveedor_id:
            query = query.filter(
                or_(
                    DetalleCierre.proveedor_id == int(proveedor_id),
                    DetalleCierre.producto.has(Producto.proveedor_id == int(proveedor_id))
                )
            )

    # 2. Filtro de Fechas
    if fecha_inicio_str and fecha_fin_str:
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
        fecha_fin = datetime.strptime(fecha_fin_str + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
        query = query.filter(CierreDia.fecha >= fecha_inicio, CierreDia.fecha <= fecha_fin)

    cierres = query.distinct().order_by(CierreDia.fecha.desc()).all()

    # 3. Construcción del Resumen
    resumen = {
        'total_esperado': 0,
        'total_transferencias': 0,
        'efectivo_caja': 0,
        'total_deudas': 0, 
        'diferencia': 0,
        'subtotal_filtrado': 0, 
        'costo_filtrado': 0,
        'ganancia_filtrada': 0,
        'productos': {} 
    }

    for c in cierres:
        resumen['total_esperado'] += c.total_esperado
        resumen['total_transferencias'] += c.total_transferencias
        resumen['efectivo_caja'] += c.efectivo_caja
        resumen['total_deudas'] += c.total_deudas
        resumen['diferencia'] += c.diferencia

        for d in c.detalles:
            # Obtener ID de propietario y proveedor (de la foto congelada o fallback al producto)
            d_prop_id = getattr(d, 'propietario_id', None) or (d.producto.propietario_id if d.producto else None)
            d_prov_id = getattr(d, 'proveedor_id', None) or (d.producto.proveedor_id if d.producto else None)

            if propietario_id and str(d_prop_id) != str(propietario_id):
                continue
            if proveedor_id and str(d_prov_id) != str(proveedor_id):
                continue

            # Priorizar precio_costo congelado en el detalle 'd'
            precio_costo_unitario = d.precio_costo if (hasattr(d, 'precio_costo') and d.precio_costo and d.precio_costo > 0) else (d.producto.precio_costo if d.producto else 0.0)
            precio_venta_unitario = d.precio_venta if (hasattr(d, 'precio_venta') and d.precio_venta is not None) else (d.producto.precio_venta if d.producto else 0.0)
            
            costo_total_item = d.vendidos * precio_costo_unitario
            ganancia_item = d.subtotal - costo_total_item

            nombre = d.nombre_producto
            if nombre not in resumen['productos']:
                resumen['productos'][nombre] = {
                    'vendidos': 0, 
                    'subtotal': 0.0,
                    'costo': 0.0,
                    'ganancia': 0.0,
                    'precio_costo': precio_costo_unitario,
                    'precio_venta': precio_venta_unitario
                }
            
            resumen['productos'][nombre]['vendidos'] += d.vendidos
            resumen['productos'][nombre]['subtotal'] += d.subtotal
            resumen['productos'][nombre]['costo'] += costo_total_item
            resumen['productos'][nombre]['ganancia'] += ganancia_item

            resumen['subtotal_filtrado'] += d.subtotal
            resumen['costo_filtrado'] += costo_total_item
            resumen['ganancia_filtrada'] += ganancia_item

    propietarios_list = Propietario.query.all()
    proveedores_list = Proveedor.query.all()

    proveedor_seleccionado = None
    whatsapp_url = ""
    
    if proveedor_id:
        proveedor_seleccionado = Proveedor.query.get(proveedor_id)
        
        if proveedor_seleccionado:
            lineas_msg = [f"Hola *{proveedor_seleccionado.nombre}*, este es el reporte de los productos vendidos:"]
            lineas_msg.append("-----------------------------")
            
            for nombre, datos in resumen['productos'].items():
                if datos['vendidos'] > 0:
                    lineas_msg.append(f"▪ {nombre}: {datos['vendidos']} uds x ${datos['precio_costo']:,.2f} = ${datos['costo']:,.2f}")
            
            lineas_msg.append("-----------------------------")
            lineas_msg.append(f"*TOTAL A PAGAR:* ${resumen['costo_filtrado']:,.2f}")
            
            texto_codificado = urllib.parse.quote("\n".join(lineas_msg))
            telefono = (proveedor_seleccionado.telefono or "").replace(" ", "").replace("+", "")
            
            if telefono:
                whatsapp_url = f"https://wa.me/{telefono}?text={texto_codificado}"
            else:
                whatsapp_url = f"https://api.whatsapp.com/send?text={texto_codificado}"
    
    return render_template('admin_cierres.html', 
                           cierres=cierres, 
                           resumen=resumen,
                           fecha_inicio=fecha_inicio_str, 
                           fecha_fin=fecha_fin_str,
                           propietario_id=propietario_id,
                           proveedor_id=proveedor_id,
                           propietarios=propietarios_list,
                           proveedores=proveedores_list,
                           whatsapp_url=whatsapp_url)

@app.route('/admin/cierres/<int:id_cierre>/detalle')
def obtener_detalle_cierre(id_cierre):
    """Devuelve los detalles de un cierre específico en formato JSON para el modal."""
    if 'user' not in session or session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'}), 403

    cierre = CierreDia.query.get_or_404(id_cierre)
    detalles = []
    
    ganancias_por_propietario = {}
    ventas_brutas_por_propietario = {}
    descuentos_por_propietario = {}

    for d in cierre.detalles:
        producto = db.session.get(Producto, d.producto_id) if hasattr(db, 'session') else Producto.query.get(d.producto_id)
        
        # Leer primero el precio de costo congelado en el detalle
        precio_costo = d.precio_costo if (hasattr(d, 'precio_costo') and d.precio_costo and d.precio_costo > 0) else (producto.precio_costo if producto else 0.0)
        
        if hasattr(d, 'propietario_nombre') and d.propietario_nombre:
            propietario_nombre = d.propietario_nombre
        elif producto and producto.propietario:
            propietario_nombre = producto.propietario.nombre
        else:
            propietario_nombre = "Sin Propietario"

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
            'total_transferencias': cierre.total_transferencias or 0.0,
            'efectivo_caja': cierre.efectivo_caja,
            'diferencia': cierre.diferencia,
            'observaciones': cierre.observaciones or ''  # <--- NUEVO: Enviar observaciones en el JSON
        },
        'detalles': detalles,
        'ganancias_propietarios': ganancias_por_propietario,
        'ventas_brutas_propietarios': ventas_brutas_por_propietario,
        'descuentos_propietarios': descuentos_por_propietario
    })
# -----------------------------------------------------------------#
# CUENTAS POR PAGAR
# -----------------------------------------------------------------#

import urllib.parse

@app.route('/admin/cuentas-por-pagar')
@app.route('/admin/cuentas-por-pagar')
def cuentas_por_pagar():
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))

    proveedor_id = request.args.get('proveedor')

    # 1. Filtro principal: SOLO cuentas con saldo pendiente > 0 y estado distinto de 'pagado'
    query = CuentaPorPagar.query.filter(
        CuentaPorPagar.monto_pendiente > 0,
        CuentaPorPagar.estado != 'pagado'
    )

    # 2. Si el usuario selecciona un proveedor en el filtro
    if proveedor_id:
        query = query.filter(CuentaPorPagar.proveedor_id == proveedor_id)

    cuentas = query.all()

    # Calcular monto total pendiente
    total_adeudado = sum(c.monto_pendiente for c in cuentas)

    # Cargar lista de proveedores para el selector desplegable
    proveedores = Proveedor.query.all()

    # Cargar historial de pagos realizados (para la tabla de abajo)
    historial = HistorialPago.query.order_by(HistorialPago.fecha_pago.desc()).all()

    # Datos adicionales para resumen de WhatsApp
    proveedor_obj = Proveedor.query.get(proveedor_id) if proveedor_id else None
    mensaje_wa = ""
    if proveedor_obj:
        detalles = []
        for c in cuentas:
            prod = Producto.query.get(c.producto_id) if c.producto_id else None
            nombre_prod = prod.nombre if prod else "Producto/Servicio"
            detalles.append(f"- {nombre_prod} (Cant: {c.cantidad}): ${c.monto_pendiente:.2f}")
        
        texto_detalles = "%0A".join(detalles)
        mensaje_wa = f"Hola {proveedor_obj.nombre}, te adjunto el resumen de cuentas pendientes:%0A%0A{texto_detalles}%0A%0ATotal pendiente: ${total_adeudado:.2f}"

    return render_template(
        'cuentas_por_pagar.html',
        cuentas=cuentas,
        total_adeudado=total_adeudado,
        proveedores=proveedores,
        proveedor_seleccionado=proveedor_id,
        proveedor_obj=proveedor_obj,
        mensaje_wa=mensaje_wa,
        historial=historial
    )

@app.route('/admin/pagar-cuenta/<int:id>', methods=['POST'])
def pagar_cuenta_proveedor(id):
    if 'user' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    cuenta = CuentaPorPagar.query.get_or_404(id)
    
    try:
        cantidad_a_pagar = int(request.form.get('cantidad_a_pagar', 1))
    except (TypeError, ValueError):
        cantidad_a_pagar = 1

    if cantidad_a_pagar <= 0:
        return redirect(url_for('cuentas_por_pagar'))
        
    # Limita a no abonar más unidades de las que quedan registradas
    cantidad_a_pagar = min(cantidad_a_pagar, cuenta.cantidad)

    # Calcular precio unitario original congelado de esta deuda
    precio_unitario = cuenta.monto_pendiente / cuenta.cantidad if cuenta.cantidad > 0 else 0
    monto_a_pagar = precio_unitario * cantidad_a_pagar

    # Registrar abono en el Historial
    nombre_prod = cuenta.producto.nombre if cuenta.producto else "Producto General"
    pago = HistorialPago(
        proveedor_nombre=cuenta.proveedor.nombre if cuenta.proveedor else "Sin Proveedor",
        producto_nombre=f"{nombre_prod} (x{cantidad_a_pagar})",
        monto_pagado=monto_a_pagar
    )
    db.session.add(pago)

    # Descontar tanto las unidades como el dinero adeudado
    cuenta.cantidad -= cantidad_a_pagar
    cuenta.monto_pendiente -= monto_a_pagar

    # Marcar como totalmente pagado si ya no restan unidades o saldo
    if cuenta.cantidad <= 0 or cuenta.monto_pendiente <= 0:
        cuenta.cantidad = 0
        cuenta.monto_pendiente = 0
        cuenta.estado = 'pagado'

    db.session.commit()
    return redirect(url_for('cuentas_por_pagar'))

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
    