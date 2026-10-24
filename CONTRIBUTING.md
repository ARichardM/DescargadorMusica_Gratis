# Contribuir a MusicBox

Gracias por ayudar a mejorar MusicBox.

1. Abre un Issue describiendo el problema o propuesta.
2. Crea una rama desde `main`.
3. Mantén los cambios enfocados y no incluyas credenciales, cookies ni multimedia.
4. Ejecuta las pruebas relacionadas antes de enviar el Pull Request.
5. Incluye capturas para cualquier cambio visual.

## Comprobaciones

```powershell
cd android-app
.\gradlew.bat testPreviewUnitTest assemblePreview
```

```powershell
.\.venv\Scripts\python.exe -m py_compile musicbox_desktop.py musicbox_cloud.py
.\.venv\Scripts\python.exe -m unittest discover -v
```

Indica qué cambió, cómo lo verificaste y si afecta Android, Windows o la sincronización.
