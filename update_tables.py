from app import app, db

with app.app_context():
    # Ejecutamos una sentencia SQL directa para crear la tabla si no existe, 
    # evitando conflictos con el MetaData de SQLAlchemy.
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS historial_perdidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            producto_nombre VARCHAR(100) NOT NULL,
            propietario_id INTEGER,
            concepto VARCHAR(100) NOT NULL,
            cantidad FLOAT NOT NULL,
            precio_costo FLOAT NOT NULL,
            monto_perdida FLOAT NOT NULL,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos (id),
            FOREIGN KEY (propietario_id) REFERENCES propietarios (id)
        )
    """))
    db.session.commit()
    print("¡Tabla 'historial_perdidas' creada con éxito mediante SQL directo!")