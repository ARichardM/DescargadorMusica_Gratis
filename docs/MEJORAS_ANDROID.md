# Revisión de MusicBox Android 2.2.0

Lista de solicitudes de esta sesión. Cada casilla se cierra después de implementar
y comprobar el comportamiento; las pruebas físicas usan **MusicBox pruebas**, con
datos privados independientes de la aplicación original.

- [x] Repetición desactivada, de lista y de canción, con modo visible y persistente.
- [x] Menú compacto de tres puntos en el reproductor: playlist, carpeta, eliminar
  y cola de reproducción, con iconos en todas las opciones.
- [x] Crear o elegir playlists y carpetas; copiar música local o descargar un tema
  online a la carpeta elegida; confirmar eliminaciones y comprobar su resultado.
- [x] Recordar la colección abierta, búsqueda, filtros y desplazamiento de Mi música.
- [x] Recuperar la canción, posición y cola al volver a abrir la aplicación.
- [x] Resaltar la canción actual en la lista y ofrecer un botón compacto para localizarla.
- [x] Collages de portadas de las canciones más escuchadas de cada carpeta y playlist,
  incluidos favoritos; contar también los avances automáticos.
- [x] Indicador de archivo descargado con flecha de descarga y tic.
- [x] Cola editable en un panel inferior: agregar varias canciones, buscar, reproducir
  después, arrastrar para ordenar, quitar y limpiar sin borrar los archivos.
- [x] Auditar gestos en todas las secciones: carruseles, listas, filtros, buscadores,
  controles, cola, reproductor y navegación. Respetar sus prioridades y cancelaciones.
- [x] Cambiar de pestaña con swipe sobre contenido adecuado sin robar el desplazamiento
  de los carruseles, incluso en los extremos, ni el desplazamiento vertical de las listas.
- [x] Conservar los botones del navbar y permitir mantener y arrastrar su selector,
  con las páginas y el indicador siguiendo el dedo.
- [x] Situar el minirreproductor debajo de la navegación; subir o bajar el navbar
  suavemente cuando el minirreproductor aparece o desaparece.
- [x] Cambiar de canción deslizando el minirreproductor, mostrando una transición
  de portada y texto que acompaña el movimiento, sin un reemplazo brusco.
- [x] Expandir el minirreproductor arrastrándolo hacia arriba, con una vista del
  reproductor que siga el dedo y se complete o se cancele suavemente al soltar.
- [x] Ocultar MP4 cuando el archivo o la fuente que se reproduce no tenga video.
- [x] Cambiar de tema sin perder biblioteca, búsqueda, resultados, filtros, posición,
  reproducción, cola ni el estado de las descargas que sigan activas.
- [x] Animar con fluidez la selección y la aparición o desaparición de filtros.
- [x] Reducir el espacio vacío de las cabeceras y aprovechar mejor la pantalla.
- [x] Unificar botones de texto con burbujas o marcos, etiquetas centradas y tamaños
  y posiciones coherentes en toda la aplicación, incluida la cola.
- [x] Proteger las zonas de acciones y botones de las canciones y del resto de
  pantallas frente a toques durante scroll, swipes o gestos cancelados.
- [x] Validar compilación, pruebas de JVM y gestos en el Samsung SM-G985F conectado
  por ADB; dejar instalada y disponible la edición de pruebas final.

## Instalación y firma

La firma del APK original pertenece al equipo de casa. La variante `preview`
utiliza `cl.arichard.descargador.pruebas` y puede convivir con la original. Para
publicar una actualización sobre la instalación original se necesitará su clave.

## Verificación del 22 de octubre de 2026

- APK `2.2.0-pruebas` compilado y con firma verificada; instalado por ADB en el
  Samsung SM-G985F con Android 13. La reproducción queda en pausa al acabar las pruebas.
- 18 pruebas de JVM: sesión y cola persistentes, navegación, repetición, controles,
  cancelación de gestos, copia de archivos y eliminación confirmada con manejo de errores.
- Siete escenarios en el teléfono: carruseles/filtros/listas, arrastre del navbar,
  cambio de tema, zonas de acciones protegidas, expansión interactiva, gestos del
  minirreproductor y controles/reordenamiento de cola/cierre del reproductor.
- `lintPreview` y comprobación de espacios de Git sin errores.
- La prueba de scroll espera a que termine la inercia y elige una canción dentro
  del área visible; evita comenzar sobre filtros que cubren filas recortadas.

El APK final se genera en `android-app/app/build/outputs/apk/preview/app-preview.apk`.
Los archivos descargados, claves, capturas del teléfono y directorios de compilación
permanecen fuera del control de versiones. Las rutas online dependen de YouTube y
de yt-dlp; estas pruebas no descargan ni eliminan archivos personales del teléfono.
