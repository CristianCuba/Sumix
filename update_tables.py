from app import app, db, CuentaPorPagar, Producto

with app.app_context():
    # Buscamos todos los productos que tienen estado 'Pagado' o 'pagado'
    productos_pagados = Producto.query.filter(
        db.func.lower(Producto.estado_pago) == 'pagado'
    ).all()
    
    ids_pagados = [p.id for p in productos_pagados]
    
    if ids_pagados:
        # Buscamos las cuentas por pagar asociadas a estos productos
        cuentas = CuentaPorPagar.query.filter(CuentaPorPagar.producto_id.in_(ids_pagados)).all()
        
        contador = 0
        for cuenta in cuentas:
            cuenta.monto_pendiente = 0.0
            cuenta.cantidad = 0
            cuenta.estado_pago = 'pagado'
            contador += 1
            
        db.session.commit()
        print(f"✅ ¡Se actualizaron {contador} deudas pendientes a estado 'PAGADO' correctamente!")
    else:
        print("⚠️ No se encontraron productos con estado 'Pagado'.")