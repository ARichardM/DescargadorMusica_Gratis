<p align="center">
  <img src="docs/images/musicbox-banner.svg" width="860" alt="MusicBox — tu música, en todos lados">
</p>

<p align="center">
  <a href="https://github.com/ARichardM/DescargadorMusica_Gratis/releases/latest"><img alt="Última versión" src="https://img.shields.io/github/v/release/ARichardM/DescargadorMusica_Gratis?style=for-the-badge&color=0A84FF"></a>
  <a href="https://github.com/ARichardM/DescargadorMusica_Gratis/actions/workflows/android-ci.yml"><img alt="Android CI" src="https://img.shields.io/github/actions/workflow/status/ARichardM/DescargadorMusica_Gratis/android-ci.yml?style=for-the-badge&label=Android"></a>
  <img alt="Android 7+" src="https://img.shields.io/badge/Android-7%2B-3DDC84?style=for-the-badge&logo=android&logoColor=white">
  <img alt="Windows" src="https://img.shields.io/badge/Windows-10%2F11-0078D4?style=for-the-badge&logo=windows11&logoColor=white">
</p>

<p align="center">
  <strong>Busca, reproduce, organiza y descarga tu música desde Android o Windows.</strong><br>
  Biblioteca sincronizada, playlists, favoritos, cola y una experiencia diseñada para tema claro y oscuro.
</p>

<p align="center">
  <a href="https://github.com/ARichardM/DescargadorMusica_Gratis/releases/latest/download/MusicBox-Android.apk"><strong>Descargar APK</strong></a>
  · <a href="https://github.com/ARichardM/DescargadorMusica_Gratis/releases">Ver versiones</a>
  · <a href="docs/GUIA_USO.md">Guía de uso</a>
</p>

> [!NOTE]
> El APK se distribuye mediante **GitHub Releases** porque supera el límite de tamaño de los archivos normales del repositorio. Android puede pedir permiso para instalar aplicaciones desde el navegador o gestor de archivos.

## Qué ofrece MusicBox

| Experiencia | Funciones |
| --- | --- |
| **Reproductor** | Audio y video, cola editable, repetición, reproducción aleatoria y cambio de canción mediante gestos. |
| **Biblioteca** | Canciones locales, carpetas y playlists con portadas, búsqueda y estado de reproducción. |
| **Playlists** | Nombre, descripción, menú de configuración y descarga automática de nuevas canciones. |
| **Favoritos** | Una playlist especial y sincronizada; el corazón agrega o elimina canciones de ella. |
| **Descargas** | MP3 o MP4, progreso, historial y archivos que permanecen en cada dispositivo. |
| **Cuenta** | Inicio con Google, preferencias sincronizadas y listado de dispositivos asociados. |
| **Diseño** | Tema claro/oscuro, dialogs adaptados, skeleton shimmer y diseño responsive. |

## Aplicaciones

### Android

- Android 7.0 o posterior (`minSdk 24`).
- Arquitecturas ARM y ARM64.
- APK autocontenido con yt-dlp y FFmpeg.
- Reproducción en segundo plano con MediaSession.
- Descargas guardadas localmente en el dispositivo.

Descarga la versión preparada desde [Releases](https://github.com/ARichardM/DescargadorMusica_Gratis/releases/latest). Para actualizar sin perder datos, instala una versión firmada con la misma clave que la anterior.

### Windows

La interfaz actual de escritorio está construida con **Python + PySide6/QML**. También se conservan herramientas históricas de importación, OCR y revisión de listas desarrolladas con Tkinter.

```powershell
git clone https://github.com/ARichardM/DescargadorMusica_Gratis.git
cd DescargadorMusica_Gratis
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe musicbox_desktop.py
```

Para usar inicio de sesión en una compilación propia debes proporcionar tus archivos locales de Firebase/OAuth. No se incluyen credenciales privadas en Git.

## Compilar Android

Necesitas JDK 17 y un archivo válido `android-app/app/google-services.json` de tu proyecto Firebase.

```powershell
cd android-app
.\gradlew.bat testPreviewUnitTest assembleDebug
```

El APK queda en `android-app/app/build/outputs/apk/debug/app-debug.apk`. La variante `preview` se instala como **MusicBox pruebas** y mantiene sus datos separados:

```powershell
.\gradlew.bat assemblePreview
```

Consulta la [documentación específica de Android](android-app/README.md) para las pruebas de gestos y la arquitectura del reproductor.

## Publicar una versión

El workflow `release-android.yml` compila, firma y adjunta `MusicBox-Android.apk` automáticamente al publicar una etiqueta `v*`.

Configura estos secretos en **Settings → Secrets and variables → Actions**:

| Secreto | Contenido |
| --- | --- |
| `GOOGLE_SERVICES_JSON_BASE64` | `google-services.json` codificado en Base64. |
| `ANDROID_KEYSTORE_BASE64` | Keystore de publicación codificado en Base64. |
| `KEYSTORE_PASSWORD` | Contraseña del keystore. |
| `KEY_ALIAS` | Alias de la clave. |
| `KEY_PASSWORD` | Contraseña de la clave. |

Después crea una etiqueta como `v2.2.0`. GitHub generará una Release con el APK descargable desde el botón superior.

## Arquitectura

```text
android-app/             Aplicación Android nativa (Java)
desktop_qml/             Interfaz QML de escritorio
musicbox_desktop.py      Backend de la aplicación para Windows
musicbox_cloud.py        Autenticación y sincronización de escritorio
descargador_gui.py       Herramienta clásica de descargas e importación
docs/                    Guías y documentación técnica
tests/                   Pruebas del proyecto de escritorio
```

Firebase sincroniza metadatos ligeros —playlists, favoritos, preferencias y dispositivos—. Los archivos multimedia permanecen en el equipo donde fueron descargados.

## Privacidad y uso responsable

- Cookies, tokens, credenciales, historiales y archivos multimedia están excluidos de Git.
- Las descargas permanecen localmente; no se suben a Firebase.
- MusicBox no es una aplicación oficial de YouTube ni de YouTube Music.
- Utiliza la aplicación únicamente con contenido que tengas derecho a descargar.

## Estado y contribuciones

MusicBox está en desarrollo activo. Revisa [CHANGELOG.md](CHANGELOG.md), propón mejoras mediante [Issues](https://github.com/ARichardM/DescargadorMusica_Gratis/issues) y consulta [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir un Pull Request. Los problemas sensibles se reportan siguiendo [SECURITY.md](SECURITY.md).

> El repositorio aún no declara una licencia. El código conserva los derechos de su autor hasta que se elija una licencia explícita.
