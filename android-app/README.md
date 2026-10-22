# Descargador móvil

Aplicación Android nativa derivada de la versión de escritorio. Permite buscar en
YouTube, pegar o compartir un enlace, reproducirlo dentro de la aplicación y guardar
una copia MP3 (192 kbps) o MP4 en `Descargas/Descargador`.

## Compilar

Abre `android-app` en Android Studio y ejecuta **Build > Build APK(s)**, o usa:

```powershell
.\gradlew.bat assembleDebug
```

El APK queda en `app/build/outputs/apk/debug/app-debug.apk`. Android 7 (API 24) o
posterior es necesario. La primera compilación descarga las dependencias y puede
tardar; el APK incluye Python, yt-dlp y FFmpeg, por lo que ocupa bastante espacio.

Desde 2.1.1 la reproducción usa MediaPlayer de Android y una fuente audiovisual
obtenida por yt-dlp. MP3 muestra la portada y mantiene el audio; MP4 conecta una
superficie de video al mismo reproductor y conserva la posición. El video mantiene
su proporción original. La preparación es asíncrona y las peticiones antiguas se
descartan al cambiar de canción. Los errores se muestran y quedan en Logcat bajo
`MusicBoxPlayer`.

La disponibilidad de reproducción y descarga depende del origen y de la versión
incorporada de yt-dlp. Para streaming se selecciona un formato con audio y video
juntos (`best[ext=mp4]/best`), cuya calidad puede ser inferior a la descarga MP4.
