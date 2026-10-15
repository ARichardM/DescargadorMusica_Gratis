import yt_dlp
import os
import sys

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
nombre_carpeta = "Musica"

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_DIR = os.path.join(application_path, nombre_carpeta)

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

video_urls = [
    "https://www.youtube.com/watch?v=zz2a9Q2Wru0",
]

# ==========================================
# 2. SEGUIMIENTO Y CAPTURA DE ERRORES
# ==========================================
descargas_completadas = 0
errores_detectados = []

# Este objeto actúa como una "red" silenciosa que solo atrapa los errores
class RastreadorErrores:
    def debug(self, msg):
        pass # Ignoramos todo el texto técnico
    def warning(self, msg):
        pass # Ignoramos advertencias menores
    def error(self, msg):
        # Guardamos el mensaje de error exacto para mostrarlo al final
        errores_detectados.append(msg)

def my_hook(d):
    global descargas_completadas
    if d['status'] == 'finished':
        descargas_completadas += 1
        print(f"✅ Descargada: {os.path.basename(d.get('filename'))}")

# ==========================================
# 3. OPCIONES DE DESCARGA
# ==========================================
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
    'ffmpeg_location': application_path,
    'extractor_args': {'youtube': {'player_client': ['android']}},
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'yes_playlist': True,
    'extract_flat': False,
    'progress_hooks': [my_hook],
    'logger': RastreadorErrores(), # Usamos nuestro rastreador silencioso
    'quiet': False, # Dejamos esto en False solo para ver la barra de progreso
}

# ==========================================
# 4. EJECUCIÓN Y RESUMEN FINAL
# ==========================================
print(f"\n📁 Carpeta destino: {DOWNLOAD_DIR}")
print("-" * 40)

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for url in video_urls:
            print("⏳ Analizando la lista de reproducción...")
            info = ydl.extract_info(url, download=False)
            
            # Contar canciones
            if 'entries' in info:
                total_pistas = info.get('playlist_count', len(list(info.get('entries', []))))
                print(f"📋 Canciones en cola: {total_pistas}")
            else:
                print("📋 Canciones en cola: 1")
            
            print("\n🚀 Iniciando descarga...")
            print("-" * 40)
            
            # Descargar
            ydl.download([url])
            
    # --- RESUMEN FINAL ---
    print("\n" + "=" * 50)
    print("📊 RESUMEN FINAL DEL PROCESO")
    print("=" * 50)
    print(f"✅ Éxitos: {descargas_completadas} canciones completadas.")
    
    if errores_detectados:
        print(f"❌ Fallos: {len(errores_detectados)} canciones no se pudieron descargar.")
        print("\nMotivos de los errores:")
        for i, error in enumerate(errores_detectados, 1):
            # Limpiamos el texto rojo de error de yt-dlp para que se lea mejor
            mensaje_limpio = error.replace('\033[0;31mERROR:\033[0m', '').replace('ERROR:', '').strip()
            print(f"  {i}. {mensaje_limpio}")
    else:
        print("✨ ¡Perfecto! Todas las canciones se descargaron sin problemas.")
        
    print("=" * 50 + "\n")

except Exception as e:
    print(f"\n💥 Error crítico que detuvo el script: {e}")