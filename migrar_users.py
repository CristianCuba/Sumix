import sqlite3

# Conectar directamente a tu base de datos SQLite
conexion = sqlite3.connect('instance/sumix.db') # O 'sumix.db' dependiendo de dónde la guardes
cursor = conexion.cursor()

# 1. Asegurarnos de que las columnas existan por si acaso
try:
    cursor.execute("ALTER TABLE usuario ADD COLUMN es_admin BOOLEAN DEFAULT 0;")
except:
    pass

try:
    cursor.execute("ALTER TABLE usuario ADD COLUMN almacen_id INTEGER;")
except:
    pass

# 2. Revisar si el usuario 'admin' ya existe (buscando en 'username' o 'usuario')
# Verificamos primero qué columnas tiene la tabla usuario
cursor.execute("PRAGMA table_info(usuario);")
columnas = [col[1] for col in cursor.fetchall()]
print("Columnas actuales en usuario:", columnas)

columna_login = 'username' if 'username' in columnas else 'usuario'

# 3. Insertar o actualizar el usuario admin
cursor.execute(f"SELECT id FROM usuario WHERE {columna_login} = 'admin'", ())
resultado = cursor.fetchone()

if resultado:
    # Si existe, nos aseguramos de que sea admin
    if 'es_admin' in columnas:
        cursor.execute(f"UPDATE usuario SET es_admin = 1 WHERE {columna_login} = 'admin'")
    print("¡El usuario 'admin' ya existía y sus permisos han sido actualizados!")
else:
    # Si no existe, lo creamos adaptándonos a las columnas reales
    if 'username' in columnas and 'es_admin' in columnas:
        cursor.execute("INSERT INTO usuario (username, password, nombre, es_admin) VALUES ('admin', '1234', 'Cristhian Hernandez', 1)")
    elif 'usuario' in columnas and 'es_admin' in columnas:
        cursor.execute("INSERT INTO usuario (usuario, password, nombre, es_admin) VALUES ('admin', '1234', 'Cristhian Hernandez', 1)")
    else:
        cursor.execute("INSERT INTO usuario (username, password, nombre) VALUES ('admin', '1234', 'Cristhian Hernandez')")
    print("¡Usuario 'admin' creado exitosamente desde la base de datos!")

conexion.commit()
conexion.close()