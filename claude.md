## Formato de commits

Usa siempre este formato exacto. Sin mencionar asistentes de IA ni co-autores.
El nombre del proyecto es **Descargador**. La versión inicial es **1.0.0** y su
etiqueta de publicación es **v1.0**.

```text
feat: Descargador vX.X.X — descripción corta

════════════════════════════════════════
NombreArchivo.py
════════════════════════════════════════
- Cambio 1
- Cambio 2

════════════════════════════════════════
OtroArchivo.py
════════════════════════════════════════
- Cambio 1

════════════════════════════════════════
SEGURIDAD  (solo si aplica)
════════════════════════════════════════
- ...

════════════════════════════════════════
ARCHIVOS NUEVOS  (solo si aplica)
════════════════════════════════════════
- Archivo.py — descripción

════════════════════════════════════════
ARCHIVOS MODIFICADOS
════════════════════════════════════════
- Archivo.py
- OtroArchivo.py

════════════════════════════════════════
CAMBIOS FUERA DEL CODIGO (ej cambios en servidor o infraestructura)
════════════════════════════════════════
- Describir únicamente acciones realmente ejecutadas fuera del código.
- Si no existen, indicar: No aplica.
```

### Reglas

- Título en español, formato `feat: Descargador vX.X.X — ...`.
- Una sección por archivo incluido en el commit, con separador `════════════════════════════════════════`.
- Descripciones en español, en primera persona del plural o impersonal.
- Sin atribución a asistentes de IA y sin línea `Co-Authored-By`.
- Usar siempre `git add .` antes de commitear para no perder archivos.
- Revisar primero `.gitignore` y después los archivos staged: nunca incluir
  cookies, credenciales, entornos virtuales, binarios externos ni descargas personales.
- No borrar ni truncar texto del commit que el usuario haya redactado.
- Incluir SEGURIDAD y ARCHIVOS NUEVOS solo cuando correspondan; conservar
  ARCHIVOS MODIFICADOS e indicar «Ninguno; commit inicial» si todos son nuevos.
- En un commit inicial, enumerar los archivos nuevos tanto en sus secciones
  individuales como en ARCHIVOS NUEVOS.
- Registrar pruebas y cambios operativos con resultados reales, sin inventar
  despliegues, migraciones ni publicaciones.
