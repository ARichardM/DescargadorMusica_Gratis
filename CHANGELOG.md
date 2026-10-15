# Historial de versiones

## Sin publicar

- Logo minimalista de música y descarga en la cabecera, la ventana y el acceso directo.
- Script para crear el acceso directo de Windows con apertura sin consola.
- Historial persistente de archivos terminados, con búsqueda, paginación y acciones
  para abrir archivos, carpetas o volver a añadir el enlace a la cola.
- Escritura del historial desde el trabajador y consultas en segundo plano.
- Los nuevos MP3 incrustan la portada y los metadatos disponibles en la fuente.
- El progreso distingue el guardado de metadatos y la incorporación de la portada.
- Las descargas de varios enlaces llevan números según su orden en la cola,
  conservando la secuencia importada desde texto o imágenes.
- Los archivos terminados se conservan sin volver a escribir sus etiquetas.
- Se fija una versión compatible de Shapely en Windows para la lectura de fotos.

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
