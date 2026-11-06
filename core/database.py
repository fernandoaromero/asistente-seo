import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'seo.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            fecha_creacion TEXT,
            fecha_publicacion TEXT,
            seo_descripcion TEXT,
            seo_tags TEXT,
            seo_gancho TEXT,
            guion TEXT,
            video_id_inspiracion TEXT,
            video_id_youtube TEXT,
            ruta_carpeta TEXT
        )
    ''')
    
    # Migración para titulo_viral
    cursor.execute("PRAGMA table_info(proyectos)")
    columnas = [info[1] for info in cursor.fetchall()]
    if 'titulo_viral' not in columnas:
        cursor.execute("ALTER TABLE proyectos ADD COLUMN titulo_viral TEXT")
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS topicos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS canales (id INTEGER PRIMARY KEY AUTOINCREMENT, handle TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ajustes (clave TEXT PRIMARY KEY, valor TEXT)''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS descartados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE,
            titulo TEXT
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM topicos")
    if cursor.fetchone()[0] == 0:
        topicos_default = ["Linux", "Windows", "Android", "Inteligencia Artificial", "WhatsApp", "Instagram", "Facebook", "Github", "Office", "Roblox", "Minecraft", "PC bajos recursos"]
        cursor.executemany("INSERT INTO topicos (nombre) VALUES (?)", [(t,) for t in topicos_default])
        
    cursor.execute("SELECT COUNT(*) FROM canales")
    if cursor.fetchone()[0] == 0:
        canales_default = ["WilDroid1", "dameunamano", "tutorialesdigitales"]
        cursor.executemany("INSERT INTO canales (handle) VALUES (?)", [(c,) for c in canales_default])
        
    cursor.execute("SELECT COUNT(*) FROM ajustes WHERE clave = 'videos_por_topico'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO ajustes (clave, valor) VALUES ('videos_por_topico', '1')")
        
    cursor.execute("SELECT COUNT(*) FROM ajustes WHERE clave = 'meses_antiguedad'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO ajustes (clave, valor) VALUES ('meses_antiguedad', '3')")

    cursor.execute("SELECT COUNT(*) FROM ajustes WHERE clave = 'gemini_api_key'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO ajustes (clave, valor) VALUES ('gemini_api_key', '')")
        
    conn.commit()
    conn.close()

def get_proyectos_por_estado(estado):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if estado == 'produccion':
        cursor.execute("SELECT * FROM proyectos WHERE estado != 'publicado' ORDER BY id DESC")
    else:
        cursor.execute("SELECT * FROM proyectos WHERE estado = 'publicado' ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insertar_proyecto(titulo, video_id_inspiracion=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    fecha = datetime.now().strftime("%d-%b-%Y")
    cursor.execute('''
        INSERT INTO proyectos (titulo, estado, fecha_creacion, video_id_inspiracion)
        VALUES (?, 'pendiente', ?, ?)
    ''', (titulo, fecha, video_id_inspiracion))
    conn.commit()
    conn.close()

def marcar_como_publicado(id_proyecto, video_id_youtube, fecha):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE proyectos 
        SET estado = 'publicado', video_id_youtube = ?, fecha_publicacion = ?
        WHERE id = ?
    ''', (video_id_youtube, fecha, id_proyecto))
    conn.commit()
    conn.close()

def get_videos_ignorados():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ignorados = set()
    cursor.execute("SELECT video_id_inspiracion FROM proyectos WHERE video_id_inspiracion IS NOT NULL")
    for row in cursor.fetchall():
        ignorados.add(row[0])
    cursor.execute("SELECT video_id FROM descartados")
    for row in cursor.fetchall():
        ignorados.add(row[0])
    conn.close()
    return ignorados

def descartar_video(video_id, titulo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO descartados (video_id, titulo) VALUES (?, ?)", (video_id, titulo))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def get_topicos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM topicos")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "nombre": r[1]} for r in rows]

def add_topico(nombre):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO topicos (nombre) VALUES (?)", (nombre,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_topico(id_topico):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM topicos WHERE id = ?", (id_topico,))
    conn.commit()
    conn.close()

def get_canales():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, handle FROM canales")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "handle": r[1]} for r in rows]

def add_canal(handle):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO canales (handle) VALUES (?)", (handle,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_canal(id_canal):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM canales WHERE id = ?", (id_canal,))
    conn.commit()
    conn.close()

def get_ajuste(clave):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM ajustes WHERE clave = ?", (clave,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""

def set_ajuste(clave, valor):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO ajustes (clave, valor) VALUES (?, ?)", (clave, str(valor)))
    conn.commit()
    conn.close()