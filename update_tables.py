from app import app, db, DeudaCierre
from datetime import datetime, timedelta

with app.app_context():
    # Calcular la fecha y hora de ayer
    ayer = datetime.now() - timedelta(days=1)
    
    # Buscar el registro específico por su ID
    deuda = DeudaCierre.query.get(10)
    
    if deuda:
        # Actualizar la fecha y guardar los cambios
        deuda.fecha = ayer
        db.session.commit()
        print(f"✅ Éxito: La fecha de la deuda con ID 10 se cambió a {ayer.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("⚠️ Error: No se encontró ninguna deuda con el ID 10 en la base de datos.")