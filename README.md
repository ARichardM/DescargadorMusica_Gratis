<p align="center">
  <img src="assets/logo.png" width="104" alt="Logo de Descargador">
</p>

# Descargador · música y video para Windows

Aplicación de escritorio para buscar videos, escucharlos y preparar descargas
**MP3 o MP4**, a partir de enlaces, nombres de canciones o imágenes de una lista.
Incluye portadas, OCR local, tabla editable, informes de pendientes e historial.

Construida con **Python y Tkinter**, con procesos separados para las tareas de
red, reconocimiento y reproducción. No es una aplicación oficial de YouTube ni
incluye una cuenta de YouTube Music.

Versión base: **1.0.0**, etiqueta **v1.0**. Las mejoras posteriores se describen en
[CHANGELOG.md](CHANGELOG.md). Para instrucciones detalladas, consulta la
[guía completa de uso](docs/GUIA_USO.md).

## Qué puedes hacer

- Descargar un video por enlace o una playlist completa/un rango.
- Elegir MP3 de 128, 192, 256 o 320 kbps; MP4 hasta 1080p o la mejor opción disponible.
- Buscar por artista o título y ver resultados con portada, canal y duración.
- Escuchar con el reproductor integrado o con la escucha rápida de audio de las coincidencias.
- Adjuntar, pegar, recortar o quitar imágenes y reconocer nombres con OCR local.
- Importar listas en texto, corregirlas en una tabla y revisar coincidencias propuestas.
- Consultar los pendientes con sus motivos y reintentar sin perder las elecciones anteriores.
- Comprobar entradas no disponibles usando el enlace de la playlist original.
- Incrustar portadas y metadatos disponibles en los MP3 y mantener el orden de la cola.
- Consultar el historial local de archivos terminados, con búsqueda y acceso a su carpeta.

## Requisitos

- **Windows**. Los iniciadores, accesos directos y el reproductor WebView2 se preparan para Windows.
- **Python 3.11 o superior recomendado**, con Tcl/Tk y pip. El código admite Python 3.10,
  pero yt-dlp avisa de su retirada de soporte. En la instalación de Python, activa
  **Add Python to PATH**.
- **FFmpeg** para convertir/unir pistas y para la escucha rápida de audio.
- **Microsoft Edge WebView2 Runtime** para el reproductor de video integrado.
- Conexión a Internet para búsquedas, reproducción y descargas. El OCR se ejecuta localmente.
- Node.js o Deno en el PATH puede ser necesario para las comprobaciones JavaScript de YouTube;
  el programa habilita el que encuentre.

## Instalación, paso a paso

1. Instala [Python](https://www.python.org/downloads/windows/) y comprueba que abre
   desde una terminal con `python --version`.
2. Descarga el ZIP del repositorio y **extráelo**, o clónalo:

   ```powershell
   git clone https://github.com/ARichardM/DescargadorMusica_Gratis.git
   cd DescargadorMusica_Gratis
   ```

3. Descarga una compilación para Windows desde los enlaces de
   [FFmpeg](https://ffmpeg.org/download.html). Copia `ffmpeg.exe` junto a
   `descargador_gui.py`, o instala FFmpeg en el PATH. Es recomendable incluir
   `ffprobe.exe`. Estos binarios no se distribuyen en el repositorio.
4. Si falta, instala [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/).
5. Haz doble clic en **`iniciar_descargador.bat`**. Crea `.venv`, instala las
   dependencias que faltan y abre la interfaz. La primera preparación puede tardar.

No muevas ni borres la carpeta del proyecto después de crear los accesos directos:
estos apuntan a sus archivos, no son una instalación independiente.

## Acceso directo con el logo

Haz doble clic en **[`crear_acceso_directo.bat`](crear_acceso_directo.bat)**.

El archivo prepara Python y las dependencias igual que el iniciador, sin abrir
la interfaz durante la preparación, y crea:

- **Descargador** en tu escritorio de Windows, también si está redirigido a OneDrive.
- **ABRIR DESCARGADOR** dentro de la carpeta del proyecto.

Ambos utilizan `assets/descargador.ico` y abren la interfaz con `pythonw.exe`, sin
una consola adicional. El `.bat` creador sí muestra una consola con el resultado
y los errores; Windows mantiene el icono genérico de los archivos `.bat`.

Puedes repetirlo para actualizar los accesos después de mover la carpeta. Si
encuentra un acceso del mismo nombre que pertenece a otro programa, crea otro con
un sufijo, sin sobrescribirlo. Necesitas conservar la carpeta `assets/`.

Alternativa manual, desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe crear_acceso_directo.py
```

## Uso rápido

### Descargar desde enlaces

1. Pega un enlace por línea.
2. Deja **Un video por enlace** para canciones individuales. Si pegaste una playlist,
   selecciona **Playlist completa o un rango**; el rango puede ser `1-10` o `1,3,5-8`.
3. Elige MP3/MP4, calidad y carpeta de destino.
4. Pulsa **Descargar** y revisa **Archivos**, **Registro** e **Historial**.

320 kbps no mejora un audio de origen de baja calidad. El contador de archivos
listos aumenta al terminar la conversión, no cuando solo termina la transferencia.

### Buscar y escuchar

Escribe en **Buscar videos** y pulsa **Buscar con portadas**. **Escuchar aquí** abre
el reproductor del programa; añadir un resultado a la cola es una acción separada.
En las coincidencias de una lista también hay **Escucha rápida · Audio**, con pausa,
tiempo y barra para desplazarse. Escuchar no crea un MP3 en la carpeta de descargas;
usa Internet y un búfer temporal. No se garantiza el acceso a todos los videos.

### Importar canciones desde texto o imágenes

1. Abre **Imágenes y nombres…**.
2. Pega nombres o una lista copiada, o adjunta imágenes y usa **Leer imágenes → texto**.
3. Revisa artista/canal y título en **Tabla de canciones**; usa el filtro y las casillas.
4. Busca las marcadas, escucha y revisa las elecciones automáticas.
5. Consulta **Informe y pendientes** y añade las elecciones revisadas a la cola.

Límites por operación: **500 consultas**, **20 imágenes**, **40 megapíxeles en total**
y hasta **25 megapíxeles por imagen**. Para detectar entradas ocultas/no disponibles,
introduce el enlace en **Playlist original**: el texto copiado por sí solo no las contiene.

## Cómo está construido

| Componente | Implementación |
| --- | --- |
| Ventanas, formularios, tablas y cola | Python, Tkinter/ttk |
| Búsqueda y extracción de información | yt-dlp y su API de Python |
| Conversión, unión, metadatos y portadas | FFmpeg y postprocesadores de yt-dlp |
| OCR y tratamiento de imágenes | RapidOCR, ONNX Runtime, Pillow y Shapely |
| Reproducción de video | pywebview + WebView2 + reproductor oficial de YouTube |
| Escucha rápida de audio | FFmpeg + sounddevice, búfer acotado en memoria |
| Historial local | SQLite, con consultas paginadas |

La interfaz intercambia eventos con trabajadores independientes. Las tareas
costosas no realizan llamadas Tk desde otro hilo; las imágenes de la interfaz se
crean en el hilo principal. Reproducir, elegir y descargar son operaciones separadas.

### Archivos principales

```text
descargador_gui.py       Entrada, opciones y trabajador de descargas
interfaz.py              Ventana principal, cola, progreso e informes
buscar_videos.py         Buscador visual con miniaturas
importar_canciones.py    Importación, revisión y búsqueda de listas
canciones.py             Adjuntos, OCR y consultas en segundo plano
tabla_canciones.py       Tabla editable y filtros
lectura_listas.py        Organización del texto reconocido
importar_texto.py        Lectura de listas copiadas por bloques
coincidencias.py         Comparación de títulos y metadatos
informe_canciones.py     Motivos, validación y duplicados
reproductor_video.py     Reproductor integrado en una ventana independiente
reproductor_audio.py     Motor de escucha rápida de audio
audio_resultados.py      Controles de audio de las coincidencias
historial.py             Persistencia SQLite
historial_gui.py         Consulta visual del historial
crear_acceso_directo.py  Accesos .lnk con logo
assets/                 Logo, iconos y archivos gráficos
tests/                  Datos de prueba y pruebas JavaScript
docs/GUIA_USO.md         Guía detallada
```

Los archivos `test_*.py` de la raíz contienen las pruebas Python. Los scripts
originales `script_musica(con_nombres).py` y `covertir.py` se conservan como legado;
para el uso habitual, utiliza la interfaz actual.

## Datos locales y privacidad

- Archivos terminados: `Descargas/` por defecto, o la carpeta elegida.
- Historial: `datos/historial.sqlite3`.
- Las imágenes para OCR se procesan localmente; las copias temporales se limpian al terminar.
- Las cookies son opcionales y se seleccionan en **Opciones avanzadas**. No se cargan
  automáticamente desde el archivo del proyecto ni desde el navegador.
- El reproductor WebView2 utiliza una sesión privada independiente del descargador.
- Las bibliotecas personales, cookies, historial, entorno virtual y accesos `.lnk`
  están excluidos de Git. No compartas cookies: contienen información de sesión.

## Actualizar y desarrollar

Después de un `git pull`, cierra y vuelve a abrir la aplicación para cargar el código
nuevo. Ejecuta **`actualizar_descargador.bat`** para actualizar las dependencias.

Ejecución manual y pruebas desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe descargador_gui.py
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m unittest test_reproductor_video -v
```

Las pruebas del reproductor ejecutan JavaScript con Node.js si está instalado.
Las pruebas de interfaz y accesos directos requieren Windows y una sesión gráfica;
algunas pruebas de conversión necesitan FFmpeg. No hace falta descargar canciones
reales para ejecutar la batería de pruebas local. El formato de commits se documenta
en [claude.md](claude.md).

## Problemas habituales

| Problema | Qué revisar |
| --- | --- |
| Python no se encuentra | Instalar Python con PATH y abrir una terminal nueva. |
| El acceso no abre después de mover la carpeta | Repetir `crear_acceso_directo.bat`. |
| Falta el icono | Conservar `assets/descargador.ico` y volver a crear los accesos. |
| Falta FFmpeg | Copiar `ffmpeg.exe` junto al programa o revisar el PATH. |
| No aparece una función nueva | Cerrar ambas ventanas, actualizar dependencias y volver a abrir. |
| YouTube responde 429 o solicita verificar sesión | Detener los reintentos masivos, comprobar YouTube en el navegador y revisar el informe. No hay un tiempo fijo de desbloqueo. |
| Video privado o reproducción integrada deshabilitada | Revisar el motivo; el programa no puede garantizar la reproducción. |
| Una lista queda con menos enlaces que elecciones | Revisar el informe: varios títulos pueden haber elegido el mismo video. |

Usa el programa solo para contenido que tengas derecho a descargar y respeta las
condiciones de los servicios. No evita restricciones, controles de acceso ni bloqueos.
Más detalle en la [guía completa](docs/GUIA_USO.md).
