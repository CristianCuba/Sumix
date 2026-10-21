from app import app, db, Producto, StockAlmacen

def limpiar_stock_inactivos():
    with app.app_context():
        inactivos = Producto.query.filter(Producto.activo == False).all()
        
        if not inactivos:
            print("No hay productos inactivos.")
            return

        print(f"Procesando {len(inactivos)} productos inactivos para llevar su stock a 0:")
        for p in inactivos:
            print(f" - Limpiando stock de: {p.nombre} (ID: {p.id})")
            
            # Poner a 0 las existencias en cada almacén para eliminar el stock fantasma
            for stock in p.stocks:
                stock.cantidad = 0.0
        
        db.session.commit()
        print("\n¡Listo! El stock fantasma de los productos inactivos se ha puesto en 0. Las vistas de Almacenes y Balance ahora coincidirán perfectamente.")

if __name__ == '__main__':
    limpiar_stock_inactivos()