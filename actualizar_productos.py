from app import db, Propietario, PrestamoTercero

# 1. Ver todos los préstamos y su propietario_id asociado
print("--- PRÉSTAMOS EN LA BD ---")
for p in PrestamoTercero.query.all():
    print(f"ID Préstamo: {p.id} | Propietario ID: {p.propietario_id} | Deudor: {p.deudor_nombre} | Estado: {p.estado}")

# 2. Ver los propietarios existentes
print("\n--- PROPIETARIOS EN LA BD ---")
for prop in Propietario.query.all():
    print(f"ID Propietario: {prop.id} | Nombre: {prop.nombre}")