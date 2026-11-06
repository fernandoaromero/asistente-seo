# Asistente SEO - Dashboard de Producción

Herramienta local de gestión de contenido para YouTube. Permite explorar tendencias reales, generar estrategias de SEO con IA, gestionar guiones, crear carpetas de producción y subir videos automáticamente a YouTube.

## ⚙️ Requisitos previos

*   Python 3.10 o superior.
*   Cuenta de Google Cloud con la **YouTube Data API v3** habilitada.
*   API Key de **Google Gemini** (se configura desde la propia interfaz web).

## 🚀 Instalación y Configuración

1. Clona el repositorio o descarga los archivos.
2. Crea y activa un entorno virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Linux/Mac
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
4. Configura las credenciales de YouTube:
*   Descarga tu archivo client_secrets.json desde Google Cloud Console.
*   Colócalo en la carpeta .seo/.

## 🎮 Uso:

1. Ejecuta la aplicación:
   ```bash
   python app.py
2. Abre tu navegador y ve a http://127.0.0.1:5000.
3. Ve a la pestaña Configuración y pega tu API Key de Gemini.
4. ¡Empieza a explorar tendencias y crear contenido!
