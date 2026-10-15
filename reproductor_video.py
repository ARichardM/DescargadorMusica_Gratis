"""Reproductor YouTube integrado en WebView2, separado del hilo de Tkinter.

No extrae audio ni utiliza las cookies del descargador. El reproductor oficial
controla la reproducción y puede rechazar videos restringidos.
"""

from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import re
import secrets
import subprocess
import sys
import threading
from urllib.parse import parse_qs, urlsplit

import descargador_gui as backend


def video_id(url):
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or parts.username or parts.password:
        raise ValueError("El reproductor requiere un enlace de YouTube.")
    if parts.hostname == "youtu.be":
        identifier = parts.path.strip("/")
    elif parts.hostname in ("youtube.com", "www.youtube.com", "music.youtube.com", "m.youtube.com"):
        identifier = parse_qs(parts.query).get("v", [""])[0]
    else:
        identifier = ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", identifier):
        raise ValueError("El enlace no contiene un identificador de video válido.")
    return identifier


def player_error(code):
    return {
        2: "El identificador del video no es válido.",
        5: "YouTube no pudo reproducir el contenido en este reproductor.",
        100: "Video no disponible: puede haber sido eliminado o marcado como privado.",
        101: "El propietario no permite reproducir este video dentro de otras aplicaciones.",
        150: "El propietario no permite reproducir este video dentro de otras aplicaciones.",
        153: "YouTube rechazó la identificación del reproductor integrado (error 153).",
        -1: "El reproductor no respondió. Comprueba tu conexión o si YouTube está bloqueando el acceso.",
    }.get(code, f"YouTube no pudo reproducir el video (código {code}).")


def player_page(identifier, title, origin, path, autoplay=True):
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", identifier):
        raise ValueError("Identificador de video no válido.")
    config = json.dumps(dict(video=identifier, origin=origin, endpoint=path + "/event", autoplay=bool(autoplay),
                             errors={str(code): player_error(code) for code in (2, 5, 100, 101, 150, 153, -1)}), ensure_ascii=True)
    safe_title = html.escape(title)
    return """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reproductor integrado</title><style>
body{margin:0;background:#f3f5fa;color:#1b2540;font:15px 'Segoe UI',sans-serif}
header,footer{padding:16px 22px}h1{font-size:19px;margin:0 0 5px}p{margin:4px 0}
#screen{background:#080811;aspect-ratio:16/9;min-height:270px;width:100%}
#player{width:100%;height:100%;min-height:270px}small{color:#69758c}a{color:#6251e8}
#status{padding-bottom:8px}.error{color:#bf354f}
</style></head><body><header><h1>""" + safe_title + """</h1>
<small>Escucha en el programa · No se crea un archivo MP3. Usa Internet y búfer temporal.</small></header>
<div id="screen"><div id="player"></div></div><footer>
<p id="status" role="status">Cargando el reproductor oficial de YouTube…</p>
<a href="https://www.youtube.com/watch?v=""" + identifier + """" target="_blank" rel="noopener">Abrir en YouTube si el video no permite reproducción integrada</a>
</footer><script>
const config=""" + config + """;
let responded=false;
function notify(status,code){
  fetch(config.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({status:status,code:code})}).catch(()=>{});
}
function message(text,error){const el=document.getElementById('status');el.textContent=text;el.className=error?'error':'';}
function failure(code){responded=true;message(config.errors[String(code)]||'YouTube rechazó la reproducción. Puedes probar el enlace inferior.',true);notify('error',code);}
function onYouTubeIframeAPIReady(){
  window.previewPlayer=new YT.Player('player',{videoId:config.video,width:'100%',height:'100%',
    playerVars:{autoplay:config.autoplay?1:0,controls:1,playsinline:1,origin:config.origin,rel:0},
    events:{
      onReady:function(){responded=true;message('Reproductor listo. Si no comienza, pulsa ▶ dentro del video.',false);notify('ready');},
      onError:function(event){failure(event.data);},
      onAutoplayBlocked:function(){responded=true;message('Pulsa ▶ dentro del video para empezar a escuchar.',false);notify('autoplay_blocked');},
      onStateChange:function(event){
        if(event.data===1){message('Reproduciendo · Puedes pausar, ajustar el volumen o adelantar con los controles del video.',false);notify('playing');}
        else if(event.data===2){message('En pausa.',false);notify('paused');}
        else if(event.data===0){message('Reproducción terminada.',false);notify('ended');}
      }
    }});
}
setTimeout(()=>{if(!responded)failure(-1);},25000);
const script=document.createElement('script');script.src='https://www.youtube.com/iframe_api';script.onerror=()=>failure(-1);document.head.appendChild(script);
</script></body></html>"""


def make_player_server(identifier, title, emit, *, autoplay=True):
    path = "/" + secrets.token_urlsafe(24)
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass

        def do_GET(self):
            if self.path != path:
                self.send_error(404)
                return
            body = player_page(identifier, title, origin, path, autoplay).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != path + "/event" or self.headers.get("Origin") != origin:
                self.send_error(403)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 1024:
                    raise ValueError("Tamaño inválido")
                data = json.loads(self.rfile.read(length))
                status = data["status"]
                if status not in ("ready", "playing", "paused", "ended", "error", "autoplay_blocked"):
                    raise ValueError("Evento inválido")
                code = data.get("code")
                if code is not None and (type(code) is not int or not -1 <= code <= 999):
                    raise ValueError("Código inválido")
                with lock:
                    emit(dict(event="player", status=status, text=player_error(code) if status == "error" else ""))
            except (KeyError, ValueError, TypeError):
                self.send_error(400)
                return
            self.send_response(204)
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    origin = f"http://127.0.0.1:{server.server_port}"
    return server, origin + path


def run_player(config):
    def emit(event):
        print(json.dumps(event, ensure_ascii=True), flush=True)

    server = None
    try:
        import webview
        identifier = video_id(config["url"])
        server, url = make_player_server(identifier, config.get("title") or "Reproductor", emit,
                                        autoplay=bool(config.get("autoplay", True)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        webview.settings["ALLOW_DOWNLOADS"] = False
        webview.settings["ALLOW_FILE_URLS"] = False
        webview.create_window("Reproductor · " + (config.get("title") or "YouTube"), url=url,
                              width=900, height=680, min_size=(640, 500), background_color="#f3f5fa")
        emit(dict(event="player", status="opening", text="Abriendo reproductor integrado…"))
        webview.start(gui="edgechromium" if os.name == "nt" else None, private_mode=True, debug=False)
        return 0
    except Exception as exc:
        emit(dict(event="player", status="error", text=f"No se pudo abrir el reproductor integrado: {exc}. En Windows requiere pywebview y Microsoft Edge WebView2 Runtime."))
        return 1
    finally:
        if server:
            server.shutdown()
            server.server_close()


class PlayerJob:
    def __init__(self):
        self.events = queue.Queue()
        self.cancelled = threading.Event()
        self.process = None

    def cancel(self):
        self.cancelled.set()
        process = self.process
        if process:
            backend.stop_process(process)

    def run(self, config):
        process = None
        try:
            if self.cancelled.is_set():
                return
            interpreter = Path(sys.executable)
            if interpreter.name.lower() == "pythonw.exe":
                interpreter = interpreter.with_name("python.exe")
            flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
            process = subprocess.Popen([str(interpreter), "-u", str(backend.APP_DIR / "descargador_gui.py"), "--player-worker"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, **flags)
            self.process = process
            process.stdin.write(json.dumps(config) + "\n")
            process.stdin.close()
            if self.cancelled.is_set():
                backend.stop_process(process)
            received = False
            for line in process.stdout:
                try:
                    event = json.loads(line)
                    if isinstance(event, dict) and event.get("event") == "player":
                        received = True
                        self.events.put(event)
                except ValueError:
                    pass
            code = process.wait()
            if (code or not received) and not self.cancelled.is_set():
                self.events.put(dict(event="player", status="error", text="El reproductor se cerró o no pudo iniciarse. Comprueba WebView2 y las dependencias."))
        except Exception as exc:
            if not self.cancelled.is_set():
                self.events.put(dict(event="player", status="error", text=f"No se pudo iniciar el reproductor: {exc}"))
        finally:
            if process:
                if process.poll() is None:
                    backend.stop_process(process)
                    process.wait()
                process.stdout.close()
            self.process = None
            self.events.put(dict(event="player_done", cancelled=self.cancelled.is_set()))
