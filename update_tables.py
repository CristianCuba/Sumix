import os
import shutil
import sqlite3
from datetime import datetime


def resolver_ruta_db():
    """Busca sumix.db en la carpeta actual o en carpetas típicas del proyecto."""
    candidatos = [
        "sumix.db",
        os.path.join("instance", "sumix.db"),
        os.path.join("data", "sumix.db"),
    ]
    for ruta in candidatos:
        if os.path.isfile(ruta):
            return os.path.abspath(ruta)
    raise FileNotFoundError(
        "No se encontró sumix.db. Asegúrate de correr este archivo desde la carpeta de tu proyecto en VS Code."
    )


def obtener_columnas(cursor, tabla):
    cursor.execute(f"PRAGMA table_info({tabla})")
    return {fila[1] for fila in cursor.fetchall()}


def hacer_respaldo(ruta_db):
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{ruta_db}.bak_{marca}"
    shutil.copy2(ruta_db, backup_path)
    return backup_path


def ejecutar_migracion():
    ruta_db = resolver_ruta_db()
    print(f"Usando base de datos: {ruta_db}")

    backup = hacer_respaldo(ruta_db)
    print(f"Respaldo guardado en: {backup}")

    conn = sqlite3.connect(ruta_db)
    cursor = conn.cursor()

    try:
        cols_compra = obtener_columnas(cursor, "compra")
        cols_item = obtener_columnas(cursor, "item_compra")

        agregadas = []

        if "estado" not in cols_compra:
            cursor.execute(
                "ALTER TABLE compra ADD COLUMN estado VARCHAR(20) DEFAULT 'PLANIFICADA'"
            )
            agregadas.append("compra.estado")

        if "total_confirmado" not in cols_compra:
            cursor.execute(
                "ALTER TABLE compra ADD COLUMN total_confirmado FLOAT DEFAULT 0.0"
            )
            agregadas.append("compra.total_confirmado")

        if "estado" not in cols_item:
            cursor.execute(
                "ALTER TABLE item_compra ADD COLUMN estado VARCHAR(20) DEFAULT 'PENDIENTE'"
            )
            agregadas.append("item_compra.estado")

        if "confirmado_en" not in cols_item:
            cursor.execute(
                "ALTER TABLE item_compra ADD COLUMN confirmado_en DATETIME"
            )
            agregadas.append("item_compra.confirmado_en")

        cursor.execute(
            "UPDATE compra SET estado = 'PLANIFICADA' WHERE estado IS NULL OR TRIM(estado) = ''"
        )
        cursor.execute(
            "UPDATE compra SET total_confirmado = 0.0 WHERE total_confirmado IS NULL"
        )
        cursor.execute(
            "UPDATE item_compra SET estado = 'PENDIENTE' WHERE estado IS NULL OR TRIM(estado) = ''"
        )

        conn.commit()

        if agregadas:
            print("Columnas creadas:", ", ".join(agregadas))
        else:
            print("Las columnas ya existían; solo se revisaron y normalizaron valores.")

        print("Listo: migración ejecutada correctamente.")
    except Exception as err:
        conn.rollback()
        print(f"Error al migrar: {err}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    ejecutar_migracion()