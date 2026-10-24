import os
import subprocess

# Definimos la ruta exacta donde están guardadas tus canciones
ruta_musica = r"C:\Users\PC\OneDrive - INACAP\Desktop\scripts_musica\Black_Clover_Music"

# Iteramos (revisamos uno por uno) todos los archivos dentro de la carpeta
for archivo in os.listdir(ruta_musica):
    
    # Filtramos para que el código solo trabaje con los archivos que terminan en ".webm"
    if archivo.endswith(".webm"):
        
        # Unimos la ruta de la carpeta con el nombre del archivo para tener la ubicación exacta del .webm
        ruta_completa_webm = os.path.join(ruta_musica, archivo)
        
        # Extraemos el nombre del archivo sin la extensión (ejemplo: "cancion.webm" se convierte en "cancion")
        nombre_base = os.path.splitext(archivo)[0]
        
        # Creamos la ruta para el nuevo archivo, agregándole la extensión ".mp3" al final
        ruta_completa_mp3 = os.path.join(ruta_musica, f"{nombre_base}.mp3")
        
        # Preparamos las instrucciones para ffmpeg (el programa que convierte el audio):
        # -i: indica cuál es el archivo de entrada.
        # -vn: le dice que quite el video (por si el .webm trae imagen).
        # -ab 192k y -ar 44100: ajustan la calidad y frecuencia del audio para que suene excelente.
        # -y: sobreescribe el archivo si por casualidad ya existía uno con ese nombre.
        comando = ['ffmpeg', '-i', ruta_completa_webm, '-vn', '-ab', '192k', '-ar', '44100', '-y', ruta_completa_mp3]
        
        print(f"Convirtiendo: {archivo} ...")
        
        # Ejecutamos el comando de forma silenciosa (para que no llene la pantalla de texto técnico)
        subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # MEDIDA DE SEGURIDAD: Comprobamos si el nuevo .mp3 se creó correctamente
        if os.path.exists(ruta_completa_mp3):
            # Si el .mp3 existe, eliminamos el archivo .webm original para ahorrar espacio
            os.remove(ruta_completa_webm)
            print(f"¡Listo! Convertido a mp3 y original eliminado.")
        else:
            # Si hubo un error y no se creó el mp3, avisamos y NO borramos el original
            print(f"Error al convertir: {archivo}. El .webm original NO fue eliminado.")

print("¡Proceso terminado por completo!")