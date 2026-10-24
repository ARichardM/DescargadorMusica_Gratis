# Contribuir a MusicBox

Gracias por ayudar a mejorar MusicBox.

1. Abre un Issue describiendo el problema o propuesta.
2. Crea una rama desde `main`.
3. Mantén los cambios enfocados y no incluyas credenciales, cookies ni multimedia.
4. Ejecuta las pruebas relacionadas antes de enviar el Pull Request.
5. Incluye capturas para cualquier cambio visual.

## Comprobaciones

```powershell
cd apps/android
.\gradlew.bat testPreviewUnitTest assemblePreview
```

```powershell
$env:PYTHONPATH = "apps/desktop"
.\.venv\Scripts\python.exe -m py_compile apps/desktop/musicbox_desktop.py apps/desktop/musicbox_cloud.py
.\.venv\Scripts\python.exe -m unittest discover -s tests/desktop -v
```

Indica qué cambió, cómo lo verificaste y si afecta Android, Windows o la sincronización.
