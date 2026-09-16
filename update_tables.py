from app import app, db

with app.app_context():
    try:
        # Añadir la columna cierre_id a la tabla deudas_cierre
        db.session.execute(db.text('ALTER TABLE deudas_cierre ADD COLUMN cierre_id INTEGER;'))
        db.session.commit()
        print("¡Columna 'cierre_id' agregada exitosamente a la tabla 'deudas_cierre'!")
    except Exception as e:
        print(f"Ocurrió un error (es posible que la columna ya exista): {e}")