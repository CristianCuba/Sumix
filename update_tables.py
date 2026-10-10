import os
import sqlite3

# Nombre de la base de datos definido en app.py
DB_NAME = 'sumix.db'

# Buscar la ruta exacta de la base de datos (soporta entorno con carpeta 'instance' o raíz)
db_path = os.path.join('instance', DB_NAME)
if not os.path.exists(db_path):
    db_path = DB_NAME

if not os.path.exists(db_path):
    print(f"❌ Error: No se encontró el archivo de base de datos '{DB_NAME}' en 'instance/' ni en la raíz.")
else:
    print(f"📂 Base de datos encontrada en: {db_path}")
    
    # Conectar y alterar la tabla
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE cierres_dia ADD COLUMN observaciones TEXT;")
        conn.commit()
        print("✅ ¡Éxito! La columna 'observaciones' fue agregada correctamente a la tabla 'cierres_dia'.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("⚠️ Aviso: La columna 'observaciones' ya existía previamente en la base de datos.")
        else:
            print(f"❌ Error al ejecutar la consulta: {e}")
    finally:
        conn.close()