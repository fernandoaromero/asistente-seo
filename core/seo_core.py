import requests
import json
import re
import time
import random
import html
from urllib.parse import quote_plus
from google import genai

PREFIJOS_INTENCION = ["trucos", "tutorial", "cómo", "guía", "aprende", "gratis", "para"]

PALABRAS_NEGRAS = [
    "oficial", "video musical", "gameplay", "episodio", "serie", 
    "trailer", "película", "canción", "mix", "album", "reaccionando"
]

def _parse_vistas(texto):
    if not texto: return 0
    texto_limpio = texto.upper().replace("VISTAS", "").replace("VIEWS", "").replace("\XA0", " ").strip()
    m = re.search(r'([\d.,]+)\s*(MIL|K|M|B|MILLON|MILLONES|THOUSAND|MILLION|BILLION)?', texto_limpio)
    if not m: return 0
    num_str = m.group(1)
    unidad = m.group(2)
    try:
        if unidad:
            num_str = num_str.replace(",", ".")
            if num_str.count(".") > 1: num_str = num_str.replace(".", "")
            num = float(num_str)
        else:
            num_str = re.sub(r'[.,]', '', num_str)
            num = float(num_str)
        if unidad in ["MIL", "K"]: num *= 1_000
        elif unidad in ["MILLON", "MILLONES", "M", "MILLION"]: num *= 1_000_000
        elif unidad in ["B", "BILLION"]: num *= 1_000_000_000
        return int(num)
    except ValueError:
        return 0

def _parse_antiguedad(texto_fecha):
    if not texto_fecha: return 9999
    texto = texto_fecha.lower()
    m = re.search(r'hace\s*(\d+)\s*([a-z]+)', texto)
    if not m: return 0 
    num = int(m.group(1))
    unidad = m.group(2)
    if unidad in ["a", "año", "años"]: return num * 365
    if unidad in ["m", "mes", "meses"]: return num * 30
    if unidad in ["s", "sem", "semana", "semanas"]: return num * 7
    if unidad in ["d", "día", "días"]: return num
    return 0

def _es_basura(titulo):
    titulo_lower = titulo.lower()
    return any(palabra in titulo_lower for palabra in PALABRAS_NEGRAS)

def _es_video_valido(titulo, fecha_texto, max_dias):
    if _es_basura(titulo): return False
    dias_antiguedad = _parse_antiguedad(fecha_texto)
    if dias_antiguedad > max_dias: return False
    return True

def _extraer_videos_json(data, limite, resultados, max_dias):
    if len(resultados) >= limite: return
    if isinstance(data, dict):
        if "videoRenderer" in data:
            v = data["videoRenderer"]
            titulo = v.get("title", {}).get("runs", [{}])[0].get("text", "")
            vistas_txt = v.get("viewCountText", {}).get("simpleText", "")
            fecha_txt = v.get("publishedTimeText", {}).get("simpleText", "")
            video_id = v.get("videoId", "")
            canal = v.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
            
            if titulo and video_id and _es_video_valido(titulo, fecha_txt, max_dias):
                resultados.append({
                    "titulo": titulo, "vistas": _parse_vistas(vistas_txt), 
                    "vistas_texto": vistas_txt, "video_id": video_id, 
                    "canal": canal, "fecha_texto": fecha_txt
                })
        elif "lockupViewModel" in data:
            v = data["lockupViewModel"]
            video_id = v.get("contentId", "")
            titulo = v.get("metadata", {}).get("lockupMetadataViewModel", {}).get("title", {}).get("content", "")
            metadatos = v.get("metadata", {}).get("lockupMetadataViewModel", {}).get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
            
            vistas_txt, fecha_txt, canal = "", "", ""
            for i, fila in enumerate(metadatos):
                for parte in fila.get("metadataParts", []):
                    txt = parte.get("text", {}).get("content", "")
                    txt_lower = txt.lower()
                    if "vista" in txt_lower or "view" in txt_lower or (re.search(r'^\d+([.,]\d+)?[KMB]?$', txt) and not vistas_txt):
                        vistas_txt = txt
                    elif re.search(r'\bhace\s*\d+', txt_lower) or re.search(r'\b(hoy|ayer)\b', txt_lower):
                        fecha_txt = txt
                    elif i == 0 and not canal and len(txt) < 50:
                        canal = txt
                        
            if titulo and video_id and _es_video_valido(titulo, fecha_txt, max_dias):
                resultados.append({
                    "titulo": titulo, "vistas": _parse_vistas(vistas_txt), 
                    "vistas_texto": vistas_txt, "video_id": video_id, 
                    "canal": canal, "fecha_texto": fecha_txt
                })
                
        for key, value in data.items():
            if key not in ["videoRenderer", "lockupViewModel"]:
                _extraer_videos_json(value, limite, resultados, max_dias)
    elif isinstance(data, list):
        for item in data:
            _extraer_videos_json(item, limite, resultados, max_dias)

def buscar_en_youtube(query, limit=50, max_dias=90):
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}&hl=es"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36", 
        "Accept-Language": "es-ES,es;q=0.9", 
        "Cookie": "SOCS=CAESHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzIaAmVzIAEaBgiA_LyaBg"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        m = re.search(r'ytInitialData\s*=\s*(\{.*?\});', r.text)
        if m:
            resultados = []
            _extraer_videos_json(json.loads(m.group(1)), limit, resultados, max_dias)
            return resultados
    except Exception as e:
        print(f"Error buscando en YT: {e}")
    return []

def obtener_tendencias(topicos, videos_por_topico, meses_antiguedad):
    resultados_finales = []
    limite = int(videos_por_topico)
    max_dias = int(meses_antiguedad) * 30
    
    for topico in topicos:
        prefijo = random.choice(PREFIJOS_INTENCION)
        query = f"{prefijo} {topico}"
        
        print(f"🔎 Buscando en YouTube: '{query}' (Filtrando > {max_dias} días)...")
        try:
            res = buscar_en_youtube(query, limit=50, max_dias=max_dias) 
            res_ordenados = sorted(res, key=lambda x: x['vistas'], reverse=True)
            res_finales = res_ordenados[:limite]
            
            print(f"   -> Encontrados {len(res_finales)} videos válidos.")
            for r in res_finales:
                r["seed_origen"] = topico
                resultados_finales.append(r)
        except Exception as e:
            print(f"   -> ⚠️ Error con el topico '{topico}': {e}")
        time.sleep(1.5) 
        
    return resultados_finales

def generar_seo_gemini(titulo, api_key):
    if not api_key:
        return None
        
    client = genai.Client(api_key=api_key)
    prompt = f"""Actúa como experto en SEO y CTR de YouTube. 
El creador quiere hacer un video basado en esta idea: '{titulo}'.
Tu tarea es reescribir ese título para hacerlo único, llamativo y con alto CTR (usando números, mayúsculas estratégicas, promesas de rapidez o curiosidad).
Además, genera la descripción, los tags y el gancho.

Devuelve ESTRICTAMENTE este formato JSON (sin markdown, sin texto extra):
{{
  "titulo_viral": "El nuevo título optimizado aquí",
  "descripcion": "Descripción optimizada con 2 párrafos",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "gancho": "Frase de retención"
}}"""
    
    modelos_fallback = ['gemini-3.8-flash', 'gemini-3.5-flash', 'gemini-2.5-flash']
    
    for intento in range(3):
        try:
            modelo = modelos_fallback[intento % len(modelos_fallback)]
            res = client.models.generate_content(model=modelo, contents=prompt)
            texto_limpio = res.text.replace("```json", "").replace("```", "").strip()
            return json.loads(texto_limpio)
        except Exception as e:
            print(f"Error en intento {intento+1} con Gemini: {e}")
            time.sleep(2)
    return None

# --- NUEVA FUNCIÓN: Extraer título desde URL de YouTube ---
def obtener_titulo_por_url(url):
    """Extrae el título y el video_id desde una URL de YouTube."""
    m = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if not m:
        return None, None
    video_id = m.group(1)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36", 
        "Accept-Language": "es-ES,es;q=0.9",
        "Cookie": "SOCS=CAESHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzIaAmVzIAEaBgiA_LyaBg"
    }
    try:
        r = requests.get(f"https://www.youtube.com/watch?v={video_id}", headers=headers, timeout=10)
        # 1. Meta og:title
        match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', r.text)
        if match:
            return html.unescape(match.group(1)), video_id
        
        # 2. Fallback: ytInitialPlayerResponse
        match = re.search(r'"title"\s*:\s*"([^"]+)"', r.text)
        if match:
            return match.group(1), video_id
    except Exception as e:
        print(f"Error obteniendo título: {e}")
    return None, video_id