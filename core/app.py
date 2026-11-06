from flask import Flask, render_template, jsonify, request
import database
import seo_core
import os
import shutil
import json
import re
import subprocess
from datetime import datetime

# YouTube API
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

app = Flask(__name__)

ruta_home = os.path.expanduser("~")
RUTA_SOFTWARE = os.path.join(ruta_home, "Vídeos", "Canales - YouTube", "Expertos en Software")
RUTA_SEO = os.path.join(RUTA_SOFTWARE, ".seo")
RUTA_PLANTILLAS = os.path.join(RUTA_SEO, "plantillas-es", "ES")
RUTA_PRODUCCION = os.path.join(RUTA_SOFTWARE, "A. Producción")
RUTA_PUBLICADOS = os.path.join(RUTA_SOFTWARE, "B. Publicados")
RUTA_CLIENT_SECRETS = os.path.join(RUTA_SEO, "client_secrets.json")
RUTA_TOKEN = os.path.join(RUTA_SEO, "token.json")

database.init_db()

def obtener_servicio_youtube():
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    if os.path.exists(RUTA_TOKEN):
        creds = Credentials.from_authorized_user_file(RUTA_TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(RUTA_CLIENT_SECRETS):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(RUTA_CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(RUTA_TOKEN, "w") as token:
            token.write(creds.to_json())
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

def comprobar_trio(ruta_carpeta):
    if not ruta_carpeta or not os.path.exists(ruta_carpeta):
        return False, None, None, None
    archivos = os.listdir(ruta_carpeta)
    videos = [f for f in archivos if f.lower().endswith(('.mp4', '.mov'))]
    if not videos: return False, None, None, None
    
    video_file = videos[0]
    nombre_base = os.path.splitext(video_file)[0]
    ruta_video = os.path.join(ruta_carpeta, video_file)
    ruta_json = os.path.join(ruta_carpeta, f"{nombre_base}.json")
    
    ruta_png = None
    for ext in ['.png', '.jpg', '.jpeg']:
        posible = os.path.join(ruta_carpeta, f"{nombre_base}{ext}")
        if os.path.exists(posible):
            ruta_png = posible
            break
            
    if os.path.exists(ruta_json) and ruta_png:
        return True, ruta_video, ruta_json, ruta_png
    return False, None, None, None

def pintar_carpeta_verde(ruta_carpeta):
    iconos_verdes = ["folder-green", "folder_color_green", "folder_verde"]
    for icono in iconos_verdes:
        try:
            subprocess.run(["gio", "set", ruta_carpeta, "metadata::custom-icon-name", icono], check=True, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            continue
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/produccion', methods=['GET'])
def api_get_produccion():
    proyectos = database.get_proyectos_por_estado('produccion')
    for p in proyectos:
        if p['estado'] == 'listo':
            trio, _, _, _ = comprobar_trio(p['ruta_carpeta'])
            p['trio_listo'] = trio
        else:
            p['trio_listo'] = False
    return jsonify(proyectos)

@app.route('/api/publicados', methods=['GET'])
def api_get_publicados():
    proyectos = database.get_proyectos_por_estado('publicado')
    return jsonify(proyectos)

@app.route('/api/proyecto/crear', methods=['POST'])
def api_crear_proyecto():
    datos = request.json
    if datos.get('titulo'):
        database.insertar_proyecto(datos.get('titulo'), datos.get('video_id'))
        return jsonify({"status": "ok"})
    return jsonify({"error": "Faltan datos"}), 400

@app.route('/api/proyecto/crear_manual', methods=['POST'])
def api_crear_proyecto_manual():
    datos = request.json
    titulo = str(datos.get('titulo') or '').strip()
    # CORRECCIÓN: Aseguramos que video_id no sea None antes de hacer .strip()
    video_id = str(datos.get('video_id') or '').strip() or None 
    
    if not titulo: 
        return jsonify({"error": "El título es obligatorio."}), 400
    database.insertar_proyecto(titulo, video_id)
    return jsonify({"status": "ok"})

@app.route('/api/detectar_link', methods=['POST'])
def api_detectar_link():
    url = request.json.get('url', '').strip()
    if not url: return jsonify({"error": "URL vacía."}), 400
    titulo, video_id = seo_core.obtener_titulo_por_url(url)
    if titulo: return jsonify({"titulo": titulo, "video_id": video_id})
    return jsonify({"error": "No se pudo extraer el título."}), 400

@app.route('/api/proyecto/<int:id>', methods=['GET'])
def api_obtener_proyecto(id):
    conn = database.sqlite3.connect(database.DB_PATH)
    conn.row_factory = database.sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proyectos WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if row: return jsonify(dict(row))
    return jsonify({"error": "No encontrado"}), 404

@app.route('/api/proyecto/<int:id>/guardar_guion', methods=['POST'])
def api_guardar_guion(id):
    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE proyectos SET guion = ? WHERE id = ?", (request.json.get('guion', ''), id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/proyecto/<int:id>/guardar_titulo', methods=['POST'])
def api_guardar_titulo(id):
    nuevo_titulo = request.json.get('titulo_viral', '')
    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE proyectos SET titulo_viral = ? WHERE id = ?", (nuevo_titulo, id))
    conn.commit()
    cursor.execute("SELECT ruta_carpeta FROM proyectos WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row and row[0]:
        ruta_json = None
        for f in os.listdir(row[0]):
            if f.endswith(".json"):
                ruta_json = os.path.join(row[0], f)
                break
        if ruta_json and os.path.exists(ruta_json):
            with open(ruta_json, "r", encoding="utf-8") as file:
                data = json.load(file)
            data["titulo"] = nuevo_titulo
            with open(ruta_json, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/proyecto/<int:id>', methods=['DELETE'])
def api_eliminar_proyecto(id):
    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT ruta_carpeta FROM proyectos WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row and row[0] and os.path.exists(row[0]):
        shutil.rmtree(row[0])
    cursor.execute("DELETE FROM proyectos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/proyecto/<int:id>/generar_seo', methods=['POST'])
def api_generar_seo(id):
    api_key = database.get_ajuste("gemini_api_key")
    if not api_key: return jsonify({"error": "Configura tu API Key de Gemini."}), 400

    conn = database.sqlite3.connect(database.DB_PATH)
    conn.row_factory = database.sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proyectos WHERE id = ?", (id,))
    proyecto = cursor.fetchone()
    conn.close()

    if not proyecto or proyecto['estado'] != 'pendiente':
        return jsonify({"error": "Proyecto no válido o ya procesado."}), 400

    titulo_base = proyecto['titulo']
    seo_data = seo_core.generar_seo_gemini(titulo_base, api_key)
    if not seo_data: return jsonify({"error": "Error con Gemini."}), 500

    nombre_base = re.sub(r'[^\w\s-]', '', titulo_base).strip()
    os.makedirs(RUTA_PRODUCCION, exist_ok=True)
    
    carpetas = [d for d in os.listdir(RUTA_PRODUCCION) if os.path.isdir(os.path.join(RUTA_PRODUCCION, d))]
    numeros = [int(re.match(r'^(\d+)', d).group(1)) for d in carpetas if re.match(r'^(\d+)', d)]
    siguiente_num = max(numeros) + 1 if numeros else 1
    
    nombre_final = f"{siguiente_num:02d}. {nombre_base}"
    destino = os.path.join(RUTA_PRODUCCION, nombre_final)

    try:
        shutil.copytree(RUTA_PLANTILLAS, destino, dirs_exist_ok=True)
        for raiz, _, archivos in os.walk(destino):
            for archivo in archivos:
                if archivo.lower().endswith(".drift"):
                    os.replace(os.path.join(raiz, archivo), os.path.join(raiz, f"{nombre_final}.drift"))
                    break

        metadata = {
            "titulo": seo_data.get("titulo_viral", titulo_base),
            "descripcion": seo_data.get("descripcion", ""),
            "tags": seo_data.get("tags", []),
            "gancho": seo_data.get("gancho", "")
        }
        with open(os.path.join(destino, f"{nombre_final}.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        conn = database.sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE proyectos SET estado = 'listo', titulo_viral = ?, seo_descripcion = ?, seo_tags = ?, seo_gancho = ?, ruta_carpeta = ? WHERE id = ?
        ''', (seo_data.get("titulo_viral", titulo_base), seo_data.get("descripcion", ""), ", ".join(seo_data.get("tags", [])), seo_data.get("gancho", ""), destino, id))
        conn.commit()
        conn.close()

        return jsonify({"status": "ok", "mensaje": f"Carpeta creada: {nombre_final}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/proyecto/<int:id>/subir', methods=['POST'])
def api_subir_video(id):
    youtube = obtener_servicio_youtube()
    if not youtube:
        return jsonify({"error": "Falta client_secrets.json o falló la autenticación."}), 401

    conn = database.sqlite3.connect(database.DB_PATH)
    conn.row_factory = database.sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proyectos WHERE id = ?", (id,))
    proyecto = cursor.fetchone()
    conn.close()

    if not proyecto or proyecto['estado'] != 'listo':
        return jsonify({"error": "Proyecto no listo para subir."}), 400

    ruta_carpeta = proyecto['ruta_carpeta']
    trio, ruta_video, ruta_json, ruta_png = comprobar_trio(ruta_carpeta)
    
    if not trio:
        return jsonify({"error": "No se encontró el trío perfecto."}), 400

    with open(ruta_json, "r", encoding="utf-8") as f:
        meta = json.load(f)

    try:
        body = {
            "snippet": {
                "title": meta.get("titulo", "Sin título"),
                "description": meta.get("descripcion", ""),
                "tags": meta.get("tags", []),
                "categoryId": "28"
            },
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
        }
        media = MediaFileUpload(ruta_video, chunksize=-1, resumable=True)
        request_yt = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request_yt.execute()
        video_id_youtube = response["id"]

        youtube.thumbnails().set(videoId=video_id_youtube, media_body=MediaFileUpload(ruta_png)).execute()

        os.makedirs(RUTA_PUBLICADOS, exist_ok=True)
        nombre_carpeta = os.path.basename(os.path.normpath(ruta_carpeta))
        destino_publicados = os.path.join(RUTA_PUBLICADOS, nombre_carpeta)
        os.makedirs(destino_publicados, exist_ok=True)

        shutil.move(ruta_video, os.path.join(destino_publicados, os.path.basename(ruta_video)))
        shutil.move(ruta_json, os.path.join(destino_publicados, os.path.basename(ruta_json)))
        shutil.move(ruta_png, os.path.join(destino_publicados, os.path.basename(ruta_png)))

        pintar_carpeta_verde(ruta_carpeta)

        fecha_pub = datetime.now().strftime("%d-%b-%Y")
        database.marcar_como_publicado(id, video_id_youtube, fecha_pub)

        return jsonify({"status": "ok", "mensaje": "Video subido a YouTube exitosamente."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- NUEVA API: REVERTIR PUBLICACIÓN ---
@app.route('/api/proyecto/<int:id>/revertir', methods=['POST'])
def api_revertir_proyecto(id):
    conn = database.sqlite3.connect(database.DB_PATH)
    conn.row_factory = database.sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proyectos WHERE id = ?", (id,))
    proyecto = cursor.fetchone()
    conn.close()

    if not proyecto or proyecto['estado'] != 'publicado':
        return jsonify({"error": "El proyecto no está publicado."}), 400

    nombre_carpeta = os.path.basename(os.path.normpath(proyecto['ruta_carpeta']))
    ruta_publicados = os.path.join(RUTA_PUBLICADOS, nombre_carpeta)

    if os.path.exists(ruta_publicados):
        for archivo in os.listdir(ruta_publicados):
            shutil.move(os.path.join(ruta_publicados, archivo), os.path.join(proyecto['ruta_carpeta'], archivo))
        os.rmdir(ruta_publicados)

    conn = database.sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE proyectos SET estado = 'listo', fecha_publicacion = NULL, video_id_youtube = NULL WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "mensaje": "Proyecto revertido a Producción. Recuerda borrar el video en YouTube manualmente."})

@app.route('/api/explorar', methods=['GET'])
def api_explorar():
    try:
        topicos = [t['nombre'] for t in database.get_topicos()]
        videos_por_topico = database.get_ajuste('videos_por_topico')
        meses_antiguedad = database.get_ajuste('meses_antiguedad')
        resultados = seo_core.obtener_tendencias(topicos, videos_por_topico, meses_antiguedad)
        ignorados = database.get_videos_ignorados()
        resultados_filtrados = [r for r in resultados if r['video_id'] not in ignorados]
        return jsonify(resultados_filtrados)
    except Exception as e:
        print(f"Error en explorar: {e}")
        return jsonify([])

@app.route('/api/descartar', methods=['POST'])
def api_descartar():
    datos = request.json
    database.descartar_video(datos.get('video_id'), datos.get('titulo'))
    return jsonify({"status": "ok"})

@app.route('/api/config', methods=['GET'])
def api_get_config():
    return jsonify({
        "topicos": database.get_topicos(),
        "canales": database.get_canales(),
        "videos_por_topico": int(database.get_ajuste('videos_por_topico')),
        "meses_antiguedad": int(database.get_ajuste('meses_antiguedad')),
        "gemini_api_key": database.get_ajuste('gemini_api_key')
    })

@app.route('/api/config/topico', methods=['POST'])
def api_add_topico():
    if database.add_topico(request.json.get('nombre')): return jsonify({"status": "ok"})
    return jsonify({"error": "El tópico ya existe"}), 400

@app.route('/api/config/topico/<int:id>', methods=['DELETE'])
def api_delete_topico(id):
    database.delete_topico(id)
    return jsonify({"status": "ok"})

@app.route('/api/config/canal', methods=['POST'])
def api_add_canal():
    if database.add_canal(request.json.get('handle')): return jsonify({"status": "ok"})
    return jsonify({"error": "El canal ya existe"}), 400

@app.route('/api/config/canal/<int:id>', methods=['DELETE'])
def api_delete_canal(id):
    database.delete_canal(id)
    return jsonify({"status": "ok"})

@app.route('/api/config/videos', methods=['POST'])
def api_set_videos():
    database.set_ajuste('videos_por_topico', request.json.get('videos'))
    return jsonify({"status": "ok"})

@app.route('/api/config/meses', methods=['POST'])
def api_set_meses():
    database.set_ajuste('meses_antiguedad', request.json.get('meses'))
    return jsonify({"status": "ok"})

@app.route('/api/config/gemini_key', methods=['POST'])
def api_set_gemini_key():
    database.set_ajuste('gemini_api_key', request.json.get('api_key', ''))
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)