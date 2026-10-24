"""Búsqueda visual de YouTube con escucha integrada y selección para la cola."""

from __future__ import annotations

import io
import queue
import threading
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import webbrowser

from PIL import Image, ImageOps, ImageTk

from canciones import ImportJob
from reproductor_video import PlayerJob
from interfaz import ACCENT, BG, GREEN, INK, LINE, MUTED, RED, SURFACE


THUMBNAIL_SIZE = (160, 90)
MAX_THUMBNAIL_BYTES = 512 * 1024


def thumbnail_url_allowed(url):
    try:
        parts = urlsplit(url)
        return parts.scheme == "https" and parts.hostname in ("i.ytimg.com", "img.youtube.com") and parts.port in (None, 443) and not parts.username and not parts.password
    except ValueError:
        return False


class ThumbnailRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        if not thumbnail_url_allowed(newurl):
            raise ValueError("La miniatura redirige a un destino no permitido.")
        return super().redirect_request(request, fp, code, message, headers, newurl)


def load_thumbnail(url):
    if not thumbnail_url_allowed(url):
        raise ValueError("Dirección de miniatura no válida.")
    request = Request(url, headers={"User-Agent": "Descargador/1.0"})
    with build_opener(ThumbnailRedirect()).open(request, timeout=8) as response:
        if not thumbnail_url_allowed(response.geturl()):
            raise ValueError("Destino de miniatura no válido.")
        data = response.read(MAX_THUMBNAIL_BYTES + 1)
    if len(data) > MAX_THUMBNAIL_BYTES:
        raise ValueError("La miniatura supera el tamaño permitido.")
    with Image.open(io.BytesIO(data)) as original:
        if original.width * original.height > 1_000_000:
            raise ValueError("La miniatura tiene demasiados píxeles.")
        rgb = original.convert("RGB")
        try:
            return ImageOps.fit(rgb, THUMBNAIL_SIZE, method=Image.Resampling.LANCZOS)
        finally:
            rgb.close()


class ThumbnailJob:
    """Solo produce imágenes PIL y mensajes: nunca crea objetos Tk en otro hilo."""
    def __init__(self, events, generation):
        self.events = events
        self.generation = generation
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()

    def run(self, candidates):
        for index, candidate in enumerate(candidates):
            if self.cancelled.is_set():
                break
            picture = None
            error = ""
            try:
                picture = load_thumbnail(candidate.get("thumbnail", ""))
            except Exception as exc:
                error = str(exc)
            if self.cancelled.is_set():
                if picture is not None:
                    picture.close()
                break
            self.events.put(dict(generation=self.generation, index=index, image=picture, error=error))


def duration_label(value):
    try:
        value = int(value)
        if value < 0:
            return "Duración desconocida"
        return f"{value // 3600}:{value // 60 % 60:02d}:{value % 60:02d}" if value >= 3600 else f"{value // 60}:{value % 60:02d}"
    except (ValueError, TypeError, OverflowError):
        return "Duración desconocida"


class VideoSearchDialog(tk.Toplevel):
    def __init__(self, parent, on_add, query="", cookies=""):
        super().__init__(parent)
        self.title("Buscar videos · Escuchar y elegir")
        self.configure(bg=BG)
        self.geometry(f"{min(960, self.winfo_screenwidth() - 60)}x{min(760, self.winfo_screenheight() - 80)}")
        self.minsize(740, 560)
        self.transient(parent)
        self.on_add, self.cookies = on_add, cookies
        self.job = self.thumbnail_job = None
        self.player_job = None
        self.player_failed = False
        self.busy = self.closing = False
        self.generation = 0
        self.thumbnail_events = queue.Queue()
        self.candidates, self.rows, self.photos = [], [], {}
        self.errors, self.warnings = [], []
        self.received_results = False
        self.poll_timer = self.start_timer = None
        self.query_var = tk.StringVar(master=self, value=query)
        self.status_var = tk.StringVar(master=self, value="Escribe un título o artista y pulsa Buscar. No se consulta mientras escribes.")
        self.choice_var = tk.StringVar(master=self, value="0 elegidos")
        self.player_status_var = tk.StringVar(master=self, value="Escucha integrada: pulsa «Escuchar aquí» en un resultado.")
        self.build_ui()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.grab_set()
        self.entry.focus_set()
        self.poll_timer = self.after(60, self.poll_events)
        if query.strip():
            self.start_timer = self.after(0, self.start_search)

    def build_ui(self):
        top = ttk.Frame(self, padding=18)
        top.pack(fill="x")
        tk.Label(top, text="Encuentra tu próximo audio", bg=BG, fg=INK,
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(top, text="Mira la portada, escucha en el reproductor del programa y elige qué añadir a descargas.",
                 bg=BG, fg=MUTED, wraplength=820, justify="left").pack(anchor="w", pady=(4, 12))
        search = ttk.Frame(top)
        search.pack(fill="x")
        self.entry = ttk.Entry(search, textvariable=self.query_var)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _: self.start_search())
        self.search_button = ttk.Button(search, text="Buscar", style="Accent.TButton", command=self.start_search)
        self.search_button.pack(side="left", padx=(8, 0))
        self.cancel_button = ttk.Button(search, text="Cancelar", command=self.cancel_search, state="disabled")
        self.cancel_button.pack(side="left", padx=(8, 0))
        self.status_label = tk.Label(top, textvariable=self.status_var, bg=BG, fg=MUTED,
                                     wraplength=820, anchor="w", justify="left")
        self.status_label.pack(fill="x", pady=(10, 0))
        self.player_status_label = tk.Label(top, textvariable=self.player_status_var, bg=BG, fg=MUTED,
                                            wraplength=820, anchor="w", justify="left")
        self.player_status_label.pack(fill="x", pady=(4, 0))
        ttk.Style(self).configure("Search.Horizontal.TProgressbar", background=ACCENT,
                                  troughcolor=LINE, borderwidth=0, thickness=5,
                                  lightcolor=LINE, darkcolor=LINE)
        self.progress = ttk.Progressbar(top, mode="determinate", maximum=100,
                                        style="Search.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(8, 0))

        footer = ttk.Frame(self, padding=(18, 10, 18, 16))
        footer.pack(side="bottom", fill="x")
        ttk.Button(footer, text="Cerrar", command=self.close).pack(side="left")
        ttk.Button(footer, text="Marcar todos", command=lambda: self.check_all(True)).pack(side="left", padx=6)
        ttk.Button(footer, text="Desmarcar", command=lambda: self.check_all(False)).pack(side="left")
        self.add_button = ttk.Button(footer, text="Añadir elegidos a la cola", style="Accent.TButton",
                                     command=self.add_selected, state="disabled")
        self.add_button.pack(side="right")
        tk.Label(footer, textvariable=self.choice_var, bg=BG, fg=MUTED).pack(side="right", padx=10)

        container = ttk.Frame(self, padding=(18, 0, 18, 0))
        container.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.cards = tk.Frame(self.canvas, bg=BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.cards, anchor="nw")
        self.cards.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self.resize_cards)
        self.bind("<MouseWheel>", self.on_wheel, add="+")
        self.empty = tk.Label(self.cards, text="Los resultados aparecerán aquí, con su miniatura.",
                              bg=BG, fg=MUTED, pady=35)
        self.empty.pack(fill="x")

    def resize_cards(self, _=None):
        width = self.canvas.winfo_width()
        self.canvas.itemconfigure(self.canvas_window, width=width)
        for row in self.rows:
            row["title"].configure(wraplength=max(200, width - 330))
            row["metadata"].configure(wraplength=max(200, width - 330))

    def on_wheel(self, event):
        widget = event.widget
        while widget is not None:
            if widget is self.canvas or widget is self.cards:
                if self.cards.winfo_reqheight() > self.canvas.winfo_height():
                    self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
                return "break"
            widget = getattr(widget, "master", None)

    def status(self, text, error=False):
        self.status_var.set(text)
        self.status_label.configure(fg=RED if error else MUTED)

    def set_busy(self, busy):
        self.busy = busy
        for widget in (self.entry, self.search_button):
            widget.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled", text="Cancelar")
        self.update_choices()

    def clear_results(self):
        if self.thumbnail_job:
            self.thumbnail_job.cancel()
        self.generation += 1
        for widget in self.cards.winfo_children():
            widget.destroy()
        # Libera variables/imágenes Tcl aquí, en el hilo de la interfaz.
        self.rows.clear()
        self.photos.clear()
        self.candidates.clear()
        self.canvas.yview_moveto(0)
        self.update_choices()

    def start_search(self):
        self.start_timer = None
        if self.busy:
            return
        query = " ".join(self.query_var.get().split())
        if not query or len(query) > 300:
            self.status("Escribe entre 1 y 300 caracteres para buscar.", error=True)
            return
        self.clear_results()
        self.errors.clear()
        self.warnings.clear()
        self.received_results = False
        self.job = ImportJob()
        self.set_busy(True)
        self.status("Buscando hasta 10 videos en YouTube…")
        self.progress.configure(mode="indeterminate", value=0)
        self.progress.start(15)
        config = dict(task="browse", query=query, cookies=self.cookies)
        threading.Thread(target=self.job.run, args=(config,), daemon=True).start()

    def show_results(self, candidates):
        # Una sola tarjeta por video, sin modificar la cola de descargas.
        seen = set()
        if hasattr(self, "empty") and self.empty.winfo_exists():
            self.empty.destroy()
        for candidate in candidates:
            if candidate["url"] not in seen:
                self.candidates.append(candidate)
                seen.add(candidate["url"])
        for index, candidate in enumerate(self.candidates):
            card = tk.Frame(self.cards, bg=SURFACE, highlightthickness=1, highlightbackground=LINE, padx=12, pady=12)
            card.pack(fill="x", pady=(0, 10))
            card.columnconfigure(1, weight=1)
            thumbnail = tk.Label(card, text="Cargando portada…", bg="#e9ecf5", fg=MUTED,
                                 width=22, height=5, font=("Segoe UI", 9))
            thumbnail.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(0, 14))
            title = tk.Label(card, text=candidate["title"], bg=SURFACE, fg=INK,
                             font=("Segoe UI", 11, "bold"), wraplength=400, anchor="w", justify="left")
            title.grid(row=0, column=1, sticky="ew", padx=(0, 10))
            metadata = tk.Label(card, text=f"{candidate.get('channel') or 'Canal desconocido'}  ·  {duration_label(candidate.get('duration'))}",
                                bg=SURFACE, fg=MUTED, anchor="w", wraplength=400, justify="left")
            metadata.grid(row=1, column=1, sticky="ew", pady=(4, 5))
            selected = tk.BooleanVar(master=self)
            check = ttk.Checkbutton(card, text="Elegir para descargar", style="Card.TCheckbutton", variable=selected, command=self.update_choices)
            check.grid(row=2, column=1, sticky="w")
            actions = ttk.Frame(card, style="Card.TFrame")
            actions.grid(row=0, column=2, rowspan=3)
            ttk.Button(actions, text="Escuchar aquí", command=lambda i=index: self.preview(i)).pack(fill="x")
            ttk.Button(actions, text="Abrir YouTube ↗", style="Link.TButton", command=lambda i=index: self.open_browser(i)).pack(fill="x", pady=(4, 0))
            self.rows.append(dict(frame=card, thumbnail=thumbnail, title=title, metadata=metadata, selected=selected))
        self.resize_cards()
        if self.candidates:
            self.thumbnail_job = ThumbnailJob(self.thumbnail_events, self.generation)
            threading.Thread(target=self.thumbnail_job.run, args=(list(self.candidates),), daemon=True).start()
        else:
            tk.Label(self.cards, text="No hay resultados para mostrar. Prueba un título más corto o el nombre del artista.",
                     bg=BG, fg=MUTED, wraplength=650, pady=30).pack(fill="x")

    def preview(self, index):
        previous = self.player_job
        self.player_job = PlayerJob()
        job = self.player_job
        self.player_failed = False
        candidate = self.candidates[index]
        self.player_status_var.set("Abriendo reproductor integrado… Usa Internet, pero no genera un MP3.")
        self.player_status_label.configure(fg=MUTED)
        def start():
            if previous:
                previous.cancel()
            job.run(dict(url=candidate["url"], title=candidate["title"]))
        threading.Thread(target=start, daemon=True).start()

    def open_browser(self, index):
        try:
            if not webbrowser.open(self.candidates[index]["url"]):
                raise OSError("No se pudo abrir el navegador predeterminado.")
            self.status("Abierto en YouTube para escuchar. No se ha añadido ni descargado ningún archivo.")
        except Exception as exc:
            self.status(f"No se pudo abrir el reproductor: {exc}", error=True)

    def update_choices(self):
        count = sum(row["selected"].get() for row in self.rows)
        self.choice_var.set(f"{count} elegido{'s' if count != 1 else ''}")
        self.add_button.configure(state="normal" if count and not self.busy else "disabled")

    def check_all(self, selected):
        for row in self.rows:
            row["selected"].set(selected)
        self.update_choices()

    def add_selected(self):
        if self.busy:
            return
        urls = [candidate["url"] for candidate, row in zip(self.candidates, self.rows) if row["selected"].get()]
        if not urls:
            self.status("Marca al menos un video para añadirlo.", error=True)
            return
        try:
            if self.on_add(urls) is False:
                self.status("No se pudo añadir a la cola; comprueba si hay una descarga activa. Se conservan tus elecciones.", error=True)
                return
        except Exception as exc:
            self.status(f"No se pudo añadir a la cola: {exc}", error=True)
            return
        self.close()

    def cancel_search(self):
        if self.busy and self.job and not self.job.cancelled.is_set():
            self.cancel_button.configure(state="disabled", text="Cancelando…")
            self.status("Cancelando la búsqueda…")
            threading.Thread(target=self.job.cancel, daemon=True).start()

    def handle_event(self, event):
        cancelled = self.job is not None and self.job.cancelled.is_set()
        if event["event"] == "import_error":
            self.errors.append(event["text"])
        elif event["event"] == "search_result" and not cancelled:
            self.received_results = True
            self.warnings = event.get("warnings", [])
            if event.get("failed"):
                self.errors.append(event.get("reason") or "No se pudo completar la búsqueda.")
            elif not event["candidates"]:
                self.errors.append(event.get("reason") or "YouTube no devolvió resultados. Prueba otro nombre.")
            self.show_results(event["candidates"])
        elif event["event"] == "job_done":
            self.progress.stop()
            self.progress.configure(mode="determinate", value=100 if self.candidates and not event["cancelled"] and not self.errors else 0)
            self.set_busy(False)
            if event["cancelled"]:
                self.status("Búsqueda cancelada. Puedes volver a buscar.")
            elif self.errors:
                self.status(" | ".join(dict.fromkeys(self.errors)), error=True)
            elif not self.received_results:
                self.status("No se recibió una respuesta completa. Vuelve a intentarlo más tarde.", error=True)
            else:
                text = f"{len(self.candidates)} resultados. «Escuchar aquí» usa el reproductor integrado; añadir a la cola no inicia la descarga."
                if self.warnings:
                    text += " Aviso: " + " | ".join(self.warnings[:2])
                self.status(text)

    def poll_events(self):
        self.poll_timer = None
        if self.job:
            for _ in range(15):
                try:
                    event = self.job.events.get_nowait()
                except queue.Empty:
                    break
                try:
                    self.handle_event(event)
                except Exception as exc:
                    self.errors.append(f"No se pudo mostrar una respuesta: {exc}")
        if self.player_job:
            for _ in range(15):
                try:
                    event = self.player_job.events.get_nowait()
                except queue.Empty:
                    break
                if event["event"] == "player":
                    state = event["status"]
                    self.player_failed = state == "error"
                    text = event.get("text") or {
                        "ready": "Reproductor listo. Pulsa ▶ dentro del video si no comienza.",
                        "playing": "Reproduciendo en la ventana del programa. Puedes pausar, ajustar volumen y adelantar.",
                        "paused": "Reproductor en pausa.", "ended": "Reproducción terminada.",
                        "autoplay_blocked": "Pulsa ▶ dentro del video para empezar a escuchar.",
                    }.get(state, "Abriendo reproductor integrado…")
                    self.player_status_var.set(text)
                    self.player_status_label.configure(fg=RED if state == "error" else GREEN if state == "playing" else MUTED)
                elif event["event"] == "player_done" and not self.player_failed:
                    self.player_status_var.set("Reproductor cerrado.")
        for _ in range(15):
            try:
                event = self.thumbnail_events.get_nowait()
            except queue.Empty:
                break
            picture = event["image"]
            try:
                if event["generation"] == self.generation and not self.closing and event["index"] < len(self.rows):
                    label = self.rows[event["index"]]["thumbnail"]
                    if picture is not None:
                        photo = ImageTk.PhotoImage(picture, master=self)
                        self.photos[event["index"]] = photo
                        label.configure(image=photo, text="", width=160, height=90)
                    else:
                        label.configure(text="Portada no disponible")
            finally:
                if picture is not None:
                    picture.close()
        if self.closing and not self.busy:
            self.destroy()
            return
        self.poll_timer = self.after(60, self.poll_events)

    def close(self):
        if self.player_job:
            threading.Thread(target=self.player_job.cancel, daemon=True).start()
        if self.thumbnail_job:
            self.thumbnail_job.cancel()
        if self.busy:
            self.closing = True
            self.cancel_search()
        else:
            self.destroy()

    def destroy(self):
        if self.player_job:
            threading.Thread(target=self.player_job.cancel, daemon=True).start()
        if self.thumbnail_job:
            self.thumbnail_job.cancel()
        for timer in (self.poll_timer, self.start_timer):
            if timer is not None:
                self.after_cancel(timer)
        self.poll_timer = self.start_timer = None
        if self.grab_current() is self:
            self.grab_release()
        super().destroy()
        self.rows.clear()
        self.photos.clear()
        while True:
            try:
                event = self.thumbnail_events.get_nowait()
            except queue.Empty:
                break
            if event["image"] is not None:
                event["image"].close()
        for name, value in list(vars(self).items()):
            if isinstance(value, (tk.Variable, tk.Misc)):
                delattr(self, name)
