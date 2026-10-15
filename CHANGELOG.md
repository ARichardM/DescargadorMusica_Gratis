# Historial de versiones

## v1.0 — 1.0.0 (2026-10-15)

Primera publicación del proyecto Descargador.

- Descargas MP3/MP4 individuales o por playlist, con calidad configurable.
- Interfaz Tkinter con progreso, cancelación y registro de resultados.
- Importación de imágenes, recortes y reconocimiento de canciones mediante OCR local.
- Lectura de listas en texto, tabla editable y filtros de búsqueda.
- Comparación de coincidencias y propuesta automática por título, artista y duración.
- Informe de pendientes, comprobación de playlists y reintento de consultas fallidas.
- Detección y confirmación de elecciones que apuntan al mismo video.
- Buscador con portadas y selección de resultados para la cola.
- Reproductor integrado basado en YouTube y WebView2, separado de la descarga.
- Pruebas automatizadas de interfaz, procesamiento, errores y reproducción integrada.

### Límites conocidos

- YouTube puede rechazar búsquedas, reproducción integrada o descargas por
  restricciones del video, verificación de sesión o límites de solicitudes.
- La reproducción integrada no importa la sesión del navegador ni las cookies
  configuradas para descargas.
- FFmpeg, WebView2, cookies y archivos multimedia no se distribuyen en el repositorio.
