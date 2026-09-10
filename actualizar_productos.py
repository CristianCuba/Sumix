from app import app, db, Producto

with app.app_context():
    # Actualiza todos los registros de la tabla Producto en una sola consulta
    filas_actualizadas = db.session.query(Producto).update(
        {Producto.propietario_id: 2}
    )
    db.session.commit()

    print(
        f"✅ ¡Listo! Se asignó el propietario_id = 2 a {filas_actualizadas} productos."
    )