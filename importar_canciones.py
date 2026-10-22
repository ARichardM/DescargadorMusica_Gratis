"""Adjuntar, recortar, reconocer y revisar canciones antes de añadir sus enlaces."""

from __future__ import annotations

import queue
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import webbrowser

from PIL import Image, ImageTk

from canciones import ImportJob, LoadImagesJob, MAX_IMAGES, MAX_QUERIES, clean_queries, organize_playlist_text, selection_to_box
from interfaz import ACCENT, BG, GREEN, INK, LINE, MUTED, RED, SURFACE
from tabla_canciones import SongTable
from importar_texto import parse_exported_playlist
from coincidencias import best_candidate
from filtro_canciones import SongFilter
from informe_canciones import playlist_url, selection_transfer, transfer_text
from reproductor_video import PlayerJob
from audio_resultados import InlineAudio


def duration_label(seconds):
    if seconds is None:
        return "—"
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


class ImportSongsDialog(tk.Toplevel):
    def __init__(self, parent, on_add, cookies="", on_transfer=None):
        super().__init__(parent)
        self.title("Canciones desde imágenes o nombres")
        self.geometry(f"{min(1120, self.winfo_screenwidth() - 60)}x{min(820, self.winfo_screenheight() - 80)}")
        self.minsize(900, 650)
        self.configure(bg=BG)
        self.transient(parent)
        self.on_add = on_add
        self.on_transfer = on_transfer
        self.transfer_report = None
        self.cookies = cookies
        self.attachments = []
        self.active = None
        self.photo = None
        self.displayed = None
        self.selection_start = self.selection_end = None
        self.job = None
        self.player_job = None
        self.player_failed = False
        self.busy = False
        self.closing = False
        self.task = None
        self.poll_timer = self.render_timer = None
        self.table_timer = None
        self.synced_text = ""
        self.query_sources = {}
        self.query_uploaders = {}
        self.search_row_ids = []
        self.search_row_groups = []
        self.last_pasted_export = ""
        self.import_summary = ""
        self.result_counts = {}
        self.errors = []
        self.selected_candidates = {}
        self.candidates = {}
        self.result_groups = {}
        self.search_outcomes = {}
        self.query_errors = {}
        self.playlist_report = None
        self.playlist_error = ""
        self.searched_queries = []
        self.controls = []
        self.status_var = tk.StringVar(value="Adjunta una imagen o escribe nombres de canciones para empezar.")
        self.image_var = tk.StringVar(value="Sin imágenes")
        self.choice_var = tk.StringVar(value="0 canciones elegidas")
        self.playlist_var = tk.StringVar(master=self)
        self.player_status_var = tk.StringVar(master=self, value="Selecciona un resultado y pulsa Reproducir para escucharlo.")
        self.build_ui()
        self.update_idletasks()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Control-v>", self.on_paste_shortcut)
        self.bind("<Escape>", lambda _: self.cancel_selection())
        self.grab_set()
        self.poll_timer = self.after(70, self.poll_events)

    def build_ui(self):
        header = ttk.Frame(self, padding=(20, 16, 20, 10))
        header.pack(fill="x")
        tk.Label(header, text="De una imagen a tu música", bg=BG, fg=INK,
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(header, text="Recorta lo que te interesa, revisa los nombres y elige las coincidencias.",
                 bg=BG, fg=MUTED).pack(anchor="w", pady=(3, 0))

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.images_tab = ttk.Frame(self.tabs, style="Card.TFrame", padding=14)
        self.table_tab = ttk.Frame(self.tabs, style="Card.TFrame", padding=14)
        self.search_tab = ttk.Frame(self.tabs, style="Card.TFrame", padding=14)
        self.tabs.add(self.images_tab, text="1 · Imágenes y texto")
        self.tabs.add(self.table_tab, text="2 · Tabla de canciones")
        self.tabs.add(self.search_tab, text="3 · Coincidencias")
        self.report_tab = ttk.Frame(self.tabs, style="Card.TFrame", padding=14)
        self.tabs.add(self.report_tab, text="4 · Informe y pendientes")
        self.build_images_tab()
        self.build_table_tab()
        self.build_search_tab()
        self.build_report_tab()
        self.tabs.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        footer = ttk.Frame(self, padding=(20, 0, 20, 16))
        footer.pack(side="bottom", fill="x", before=self.tabs)
        self.status_label = tk.Label(footer, textvariable=self.status_var, bg=BG, fg=MUTED,
                                    anchor="w", justify="left", wraplength=760)
        self.status_label.pack(anchor="w", fill="x")
        ttk.Style(self).configure("Import.Horizontal.TProgressbar", background=ACCENT,
                                  troughcolor=LINE, borderwidth=0, thickness=6,
                                  lightcolor=LINE, darkcolor=LINE)
        self.progress = ttk.Progressbar(footer, maximum=100, style="Import.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(8, 10))
        buttons = ttk.Frame(footer)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Cerrar", command=self.close).pack(side="left")
        self.cancel_button = ttk.Button(buttons, text="Cancelar operación", state="disabled", command=self.cancel_job)
        self.cancel_button.pack(side="left", padx=8)
        self.add_button = ttk.Button(buttons, text="Añadir elegidas a descargas", style="Accent.TButton",
                                     state="disabled", command=self.add_selected)
        self.add_button.pack(side="right")
        tk.Label(buttons, textvariable=self.choice_var, bg=BG, fg=MUTED).pack(side="right", padx=14)

    def build_images_tab(self):
        self.images_tab.columnconfigure(0, weight=0, minsize=180)
        self.images_tab.columnconfigure(1, weight=3, minsize=260)
        self.images_tab.columnconfigure(2, weight=2, minsize=250)
        self.images_tab.rowconfigure(0, weight=1)
        sidebar = ttk.Frame(self.images_tab, style="Card.TFrame")
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        ttk.Label(sidebar, text="IMÁGENES ADJUNTAS", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.attach_button = ttk.Button(sidebar, text="Adjuntar imágenes…", command=self.attach_files)
        self.attach_button.pack(fill="x")
        self.paste_button = ttk.Button(sidebar, text="Pegar imagen", command=self.paste_image)
        self.paste_button.pack(fill="x", pady=(6, 12))
        self.image_list = tk.Listbox(sidebar, height=7, width=21, bg="#f8f9fc", fg=INK,
                                     selectbackground="#e9e4ff", selectforeground=INK,
                                     exportselection=False, borderwidth=0, highlightthickness=1,
                                     highlightbackground=LINE, activestyle="none")
        self.image_list.pack(fill="both", expand=True)
        self.image_list.bind("<<ListboxSelect>>", self.select_image)
        self.image_list.bind("<Delete>", lambda _: self.remove_image())
        self.remove_button = ttk.Button(sidebar, text="Quitar imagen", command=self.remove_image)
        self.remove_button.pack(fill="x", pady=(8, 0))
        self.clear_button = ttk.Button(sidebar, text="Quitar todas", style="Link.TButton", command=self.clear_images)
        self.clear_button.pack(fill="x", pady=(4, 0))
        ttk.Label(sidebar, text="Los originales se conservan.", style="Muted.TLabel", font=("Segoe UI", 9), wraplength=175).pack(anchor="w", pady=(8, 0))

        preview = ttk.Frame(self.images_tab, style="Card.TFrame")
        preview.grid(row=0, column=1, sticky="nsew", padx=(0, 14))
        ttk.Label(preview, text="VISTA PREVIA", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.canvas = tk.Canvas(preview, bg="#f5f6fa", highlightthickness=1, highlightbackground=LINE,
                                width=300, height=260, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.schedule_render)
        self.canvas.bind("<ButtonPress-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.drag_selection)
        self.canvas.bind("<ButtonRelease-1>", self.drag_selection)
        ttk.Label(preview, textvariable=self.image_var, style="Muted.TLabel", font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))
        ttk.Label(preview, text="Arrastra sobre la imagen para marcar un recorte.", style="Muted.TLabel",
                  wraplength=300, font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 8))
        tools = ttk.Frame(preview, style="Card.TFrame")
        tools.pack(fill="x")
        self.crop_button = ttk.Button(tools, text="Recortar selección", command=self.crop_selected)
        self.crop_button.pack(side="left")
        self.restore_button = ttk.Button(tools, text="Restaurar", style="Link.TButton", command=self.restore_image)
        self.restore_button.pack(side="right")

        names = ttk.Frame(self.images_tab, style="Card.TFrame")
        names.grid(row=0, column=2, sticky="nsew")
        ttk.Label(names, text="TEXTO DE LA IMAGEN", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(names, text="Pega nombres por línea o una lista con título, artista, álbum y duración.",
                  style="Muted.TLabel", wraplength=280, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 10))
        text_views = ttk.Notebook(names)
        text_views.pack(fill="both", expand=True)
        organized = ttk.Frame(text_views, style="Card.TFrame")
        original = ttk.Frame(text_views, style="Card.TFrame")
        text_views.add(organized, text="Texto organizado")
        text_views.add(original, text="OCR original")
        self.names = scrolledtext.ScrolledText(organized, width=24, height=8, wrap="word", bg="#f8f9fc", fg=INK,
                                              insertbackground=ACCENT, relief="flat", padx=10, pady=10,
                                              font=("Segoe UI", 10), undo=True)
        self.names.pack(fill="both", expand=True)
        self.names.bind("<<Modified>>", self.names_changed)
        self.raw_text = scrolledtext.ScrolledText(original, width=24, height=8, wrap="word", bg="#f8f9fc", fg=MUTED,
                                                 relief="flat", padx=10, pady=10, font=("Segoe UI", 10), state="disabled")
        self.raw_text.pack(fill="both", expand=True)
        name_actions = ttk.Frame(names, style="Card.TFrame")
        name_actions.pack(side="bottom", fill="x", before=text_views)
        self.clean_button = ttk.Button(name_actions, text="Limpiar texto de lista", style="Link.TButton", command=self.clean_playlist_text)
        self.clean_button.pack(fill="x", pady=(5, 0))
        self.ocr_button = ttk.Button(name_actions, text="Leer imágenes → texto", command=self.start_ocr)
        self.ocr_button.pack(fill="x", pady=(10, 6))
        self.search_button = ttk.Button(name_actions, text="Revisar tabla →", style="Accent.TButton", command=self.review_table)
        self.search_button.pack(fill="x")
        self.controls.extend([self.attach_button, self.paste_button, self.remove_button, self.clear_button,
                              self.crop_button, self.restore_button, self.ocr_button, self.search_button, self.clean_button])
        self.update_image_controls()

    def build_table_tab(self):
        self.songs = SongTable(self.table_tab, self.on_table_changed, lambda text: self.status(text, error=True))
        self.songs.pack(fill="both", expand=True)
        actions = ttk.Frame(self.table_tab, style="Card.TFrame")
        actions.pack(side="bottom", fill="x", pady=(12, 0), before=self.songs)
        ttk.Button(actions, text="← Ver imágenes y texto", style="Link.TButton",
                   command=lambda: self.tabs.select(self.images_tab)).pack(side="left")
        self.table_search_button = ttk.Button(actions, text="Buscar canciones marcadas →", style="Accent.TButton", command=self.start_search)
        self.table_search_button.pack(side="right")
        self.controls.append(self.table_search_button)
        source = ttk.Frame(self.table_tab, style="Card.TFrame")
        source.pack(fill="x", before=self.songs, pady=(0, 8))
        ttk.Label(source, text="Playlist original (opcional):", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        self.playlist_entry = ttk.Entry(source, textvariable=self.playlist_var)
        self.playlist_entry.pack(side="left", fill="x", expand=True)
        self.playlist_button = ttk.Button(source, text="Comprobar", command=self.check_playlist)
        self.playlist_button.pack(side="left", padx=(8, 0))
        self.controls.extend([self.playlist_entry, self.playlist_button])
        ttk.Label(self.table_tab, text=f"Hasta {MAX_QUERIES} consultas por búsqueda. El filtro no cambia las canciones marcadas.",
                  style="Muted.TLabel").pack(side="bottom", fill="x", before=self.songs, pady=(6, 0))

    def build_search_tab(self):
        ttk.Label(self.search_tab, text="Solo se marcan automáticamente coincidencias verificables. Las dudosas quedan para revisión; puedes elegirlas con doble clic y escucharlas con ▶.",
                  style="Muted.TLabel", wraplength=880).pack(anchor="w", pady=(0, 12))
        self.results_filter = SongFilter(self.search_tab, self.filter_results)
        self.results_filter.pack(fill="x", pady=(0, 10))
        tree_frame = ttk.Frame(self.search_tab, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True)
        self.results = ttk.Treeview(tree_frame, columns=("channel", "duration", "chosen", "audio"), selectmode="browse")
        self.results.heading("#0", text="CANCIÓN / RESULTADOS")
        self.results.heading("channel", text="CANAL")
        self.results.heading("duration", text="DURACIÓN")
        self.results.heading("chosen", text="ELECCIÓN")
        self.results.heading("audio", text="ESCUCHA RÁPIDA · AUDIO")
        self.results.column("#0", width=340, minwidth=150, stretch=False)
        self.results.column("channel", width=140, minwidth=70, stretch=False)
        self.results.column("duration", width=70, minwidth=60, stretch=False, anchor="center")
        self.results.column("chosen", width=120, minwidth=105, stretch=False, anchor="center")
        self.results.column("audio", width=250, minwidth=250, stretch=False)
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.results.yview)
        self.inline_audio = InlineAudio(self.results, self.candidates, cookies=self.cookies,
            before_play=self.stop_preview, status=self.audio_status, changed=self.update_preview_controls)

        def on_scroll(first, last):
            scroll.set(first, last)
            self.inline_audio.schedule()

        self.results.configure(yscrollcommand=on_scroll)
        self.results.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.results.tag_configure("chosen", foreground=GREEN)
        self.results.tag_configure("query", foreground=ACCENT)
        self.results.bind("<Double-1>", self.choose_result)
        self.results.bind("<Return>", self.choose_result)
        self.results.bind("<<TreeviewSelect>>", lambda _: self.update_preview_controls())
        tools = ttk.Frame(self.search_tab, style="Card.TFrame")
        tools.pack(side="bottom", fill="x", pady=(8, 0), before=tree_frame)
        ttk.Button(tools, text="← Tabla", style="Link.TButton", command=lambda: self.tabs.select(self.table_tab)).pack(side="left")
        self.choose_button = ttk.Button(tools, text="Elegir / quitar resultado", command=self.choose_result)
        self.choose_button.pack(side="right")
        self.view_button = ttk.Button(tools, text="Ver en YouTube", command=self.view_result)
        self.view_button.pack(side="right", padx=8)
        self.controls.extend([self.choose_button, self.view_button])
        self.play_button = ttk.Button(tools, text="▶ Reproducir", command=self.preview_result, state="disabled")
        self.play_button.pack(side="left", padx=(8, 4))
        self.stop_player_button = ttk.Button(tools, text="Detener", command=self.stop_playback, state="disabled")
        self.stop_player_button.pack(side="left")
        self.player_status_label = ttk.Label(self.search_tab, textvariable=self.player_status_var,
            style="Muted.TLabel", wraplength=820, font=("Segoe UI", 9))
        self.player_status_label.pack(side="bottom", fill="x", pady=(6, 0), before=tools)

    def build_report_tab(self):
        ttk.Label(self.report_tab, text="Aquí se muestran todas las canciones pendientes, los motivos y las entradas no disponibles de la playlist comprobada.",
                  style="Muted.TLabel", wraplength=840).pack(anchor="w", pady=(0, 10))
        self.report_text = scrolledtext.ScrolledText(self.report_tab, wrap="word", bg="#f8f9fc", fg=INK,
                                                     relief="flat", padx=12, pady=12, state="disabled",
                                                     font=("Segoe UI", 10), height=5)
        self.report_text.pack(fill="both", expand=True)
        actions = ttk.Frame(self.report_tab, style="Card.TFrame")
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Ver coincidencias", command=lambda: self.tabs.select(self.search_tab)).pack(side="left")
        ttk.Button(actions, text="Copiar informe", command=self.copy_report).pack(side="left", padx=6)
        ttk.Button(actions, text="Guardar informe…", command=self.save_report).pack(side="left")
        self.retry_button = ttk.Button(actions, text="Reintentar pendientes", style="Accent.TButton",
                                       command=self.retry_pending, state="disabled")
        self.retry_button.pack(side="right")
        self.update_report()

    def pending_indices(self, retryable=False):
        return [index for index in range(len(self.searched_queries)) if index not in self.selected_candidates
                and (not retryable or not self.search_outcomes.get(index, {}).get("candidates"))]

    def update_report(self):
        if not hasattr(self, "report_text"):
            return
        lines = ["INFORME DE CANCIONES", ""]
        source = self.playlist_report
        if source:
            lines.extend([f"Playlist: {source['title']}",
                          f"{source['total']} entradas en total · {source['readable']} con título · {len(source['unavailable'])} no disponibles en la consulta."])
            for item in source["unavailable"]:
                lines.extend([f"  Posición {item['position']}: {item['title']}", f"  Motivo: {item['reason']}",
                              f"  Enlace: {item['url'] or 'YouTube no proporcionó un enlace.'}", ""])
            if source.get("unaccounted"):
                lines.append(f"ATENCIÓN: faltan por comprobar {source['unaccounted']} entradas; YouTube devolvió una lista incompleta.")
        elif self.playlist_error:
            lines.extend(["NO SE PUDO COMPROBAR LA PLAYLIST", self.playlist_error])
        else:
            lines.append("Playlist original sin comprobar. El texto copiado no permite detectar entradas ocultas/no disponibles. Pega el enlace en «Tabla de canciones → Playlist original» y pulsa «Comprobar».")
        lines.append("")
        ambiguous = [(number, entry) for number, (_, entry) in enumerate(self.songs.entries(), 1)
                     if entry.review_reason]
        if ambiguous:
            lines.extend([f"IMPORTACIÓN: {len(ambiguous)} bloques ambiguos; se importaron sin dividir y sin marcar.", ""])
            for number, entry in ambiguous:
                lines.extend([f"Fila {number}: {entry.title}", entry.review_reason,
                              "Texto original:", entry.raw_text, ""])
        if self.searched_queries:
            pending = self.pending_indices()
            lines.extend([f"BÚSQUEDA: {len(self.searched_queries)} consultas únicas · {len(self.selected_candidates)} elegidas · {len(pending)} pendientes.",
                          "Las entradas no disponibles de la playlist y los pendientes de búsqueda son recuentos separados.", ""])
            source_rows = sum(len(group) for group in self.search_row_groups)
            if source_rows > len(self.searched_queries):
                lines.extend([f"TABLA: {source_rows} filas marcadas → {len(self.searched_queries)} consultas únicas; "
                              f"{source_rows - len(self.searched_queries)} repeticiones agrupadas. No son errores ni canciones perdidas.", ""])
            for index in pending:
                outcome = self.search_outcomes.get(index)
                if outcome is None:
                    reason = self.query_errors.get(index) or "Consulta no completada (cancelación o cierre inesperado del proceso). Reintenta."
                elif outcome.get("candidates"):
                    reason = outcome.get("auto_review_reason") or "Hay alternativas, pero ninguna está elegida. Revisa «Coincidencias» y selecciona una."
                else:
                    reason = outcome.get("reason") or self.query_errors.get(index) or "YouTube no devolvió alternativas utilizables; revisa el nombre o reintenta."
                lines.extend([f"{index + 1}. {self.searched_queries[index]}", f"   {'ERROR' if outcome and outcome.get('failed') else 'PENDIENTE'}: {reason}", ""])
            for index, outcome in sorted(self.search_outcomes.items()):
                attempts = outcome.get("search_attempts", [])
                if len(attempts) > 1:
                    lines.extend([f"Consultas de {self.searched_queries[index]}:",
                                  *[f"  • {attempt['query']} → {attempt['received']} resultados; {attempt['skipped']} descartados."
                                    for attempt in attempts], ""])
                if outcome.get("warnings"):
                    lines.extend([f"Advertencias de {self.searched_queries[index]}:", *outcome["warnings"], ""])
        else:
            lines.append("Todavía no se ha buscado ninguna canción por nombre.")
        if self.errors:
            lines.extend(["REGISTRO DE LA ÚLTIMA OPERACIÓN", *self.errors])
        if self.transfer_report:
            lines.extend(["", transfer_text(self.transfer_report)])
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", "\n".join(lines))
        self.report_text.configure(state="disabled")
        self.retry_button.configure(state="normal" if self.pending_indices(retryable=True) and not self.busy else "disabled")

    def copy_report(self):
        self.clipboard_clear()
        self.clipboard_append(self.report_text.get("1.0", "end-1c"))
        self.status("Informe copiado al portapapeles.")

    def save_report(self):
        path = filedialog.asksaveasfilename(parent=self, title="Guardar informe de canciones", defaultextension=".txt",
                                          initialfile="informe_canciones.txt", filetypes=[("Texto", "*.txt")])
        if path:
            try:
                Path(path).write_text(self.report_text.get("1.0", "end-1c"), encoding="utf-8")
                self.status("Informe guardado.")
            except OSError as exc:
                self.status(f"No se pudo guardar el informe: {exc}", error=True)

    def check_playlist(self):
        if self.busy:
            return
        try:
            url = playlist_url(self.playlist_var.get())
            if not url:
                raise ValueError("Pega el enlace de la playlist original para comprobar sus entradas.")
        except ValueError as exc:
            self.status(str(exc), error=True)
            return
        self.playlist_report = None
        self.playlist_error = ""
        self.start_job(dict(task="playlist", playlist_url=url, cookies=self.cookies))

    def retry_pending(self):
        if self.busy:
            return
        indices = self.pending_indices(retryable=True)
        if not indices:
            return
        for index in indices:
            self.remove_query_results(index)
            self.search_outcomes.pop(index, None)
            self.query_errors.pop(index, None)
            if index < len(self.search_row_ids):
                self.set_search_state(index, "En cola")
        self.tabs.select(self.search_tab)
        self.status(f"Reintentando {len(indices)} pendientes. Se conservan las elecciones anteriores.")
        self.start_job(dict(task="search", queries=[self.searched_queries[i] for i in indices], query_indices=indices, cookies=self.cookies))

    def remove_query_results(self, index):
        for parent in list(self.result_groups):
            # Las consultas están deduplicadas; cada nombre corresponde a un grupo.
            if self.result_groups[parent] == self.searched_queries[index]:
                for child in self.results.get_children(parent):
                    self.inline_audio.remove(child)
                    self.candidates.pop(child, None)
                self.results.delete(parent)
                del self.result_groups[parent]

    def status(self, text, error=False):
        self.status_var.set(text)
        self.status_label.configure(fg=RED if error else MUTED)

    def attach_files(self):
        paths = filedialog.askopenfilenames(parent=self, title="Adjuntar imágenes con nombres de canciones",
                                           filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("Todos", "*.*")])
        self.add_paths(paths)

    def add_paths(self, paths):
        if self.busy or not paths:
            return
        self.start_loading(paths=paths)

    def paste_image(self):
        if self.busy:
            return
        self.start_loading(clipboard=True)

    def start_loading(self, paths=(), clipboard=False):
        self.errors.clear()
        self.task = "load"
        self.job = LoadImagesJob()
        self.set_busy(True)
        self.progress.configure(value=0, mode="indeterminate")
        self.progress.start(15)
        self.status("Cargando imágenes…")
        used_pixels = sum(item.original.width * item.original.height for item in self.attachments)
        threading.Thread(target=self.job.run, kwargs=dict(paths=paths, clipboard=clipboard,
                         slots=MAX_IMAGES - len(self.attachments), used_pixels=used_pixels), daemon=True).start()

    def on_paste_shortcut(self, _):
        if isinstance(self.focus_get(), (tk.Text, tk.Entry, ttk.Entry)):
            return
        self.paste_image()
        return "break"

    def refresh_attachments(self, selected=0):
        self.image_list.configure(state="normal")
        self.image_list.delete(0, "end")
        for attachment in self.attachments:
            self.image_list.insert("end", attachment.name)
        if self.attachments:
            selected = max(0, min(selected, len(self.attachments) - 1))
            self.image_list.selection_set(selected)
            self.image_list.see(selected)
            self.active = selected
        else:
            self.active = None
        self.cancel_selection()
        self.render_preview()
        self.update_image_controls()
        self.image_list.configure(state="disabled" if self.busy else "normal")

    def select_image(self, _=None):
        selected = self.image_list.curselection()
        if selected and not self.busy:
            self.active = selected[0]
            self.cancel_selection()
            self.render_preview()

    def update_image_controls(self):
        for widget in (self.remove_button, self.clear_button, self.restore_button, self.ocr_button):
            widget.configure(state="normal" if self.attachments and not self.busy else "disabled")
        self.crop_button.configure(state="normal" if self.selection_end and not self.busy else "disabled")

    def remove_image(self):
        if self.active is None or self.busy:
            return
        self.attachments.pop(self.active).close()
        self.refresh_attachments(self.active)
        self.status("Imagen retirada del programa. El archivo original se conserva.")

    def clear_images(self):
        if self.busy:
            return
        for attachment in self.attachments:
            attachment.close()
        self.attachments.clear()
        self.refresh_attachments()
        self.status("Adjuntos retirados. El texto que ya extrajiste se conserva para que puedas editarlo.")

    def schedule_render(self, _=None):
        if self.render_timer is not None:
            self.after_cancel(self.render_timer)
        self.render_timer = self.after(60, self.render_preview)

    def render_preview(self):
        self.render_timer = None
        self.canvas.delete("all")
        self.photo = self.displayed = None
        self.selection_start = self.selection_end = None
        width, height = max(40, self.canvas.winfo_width()), max(40, self.canvas.winfo_height())
        if self.active is None:
            self.canvas.create_text(width / 2, height / 2, text="Adjunta o pega una imagen\npara verla aquí", fill=MUTED,
                                     justify="center", font=("Segoe UI", 11))
            self.image_var.set("Sin imágenes")
        else:
            attachment = self.attachments[self.active]
            thumbnail = attachment.image.copy()
            thumbnail.thumbnail((max(16, width - 16), max(16, height - 16)), Image.Resampling.LANCZOS)
            x, y = (width - thumbnail.width) // 2, (height - thumbnail.height) // 2
            self.displayed = (x, y, thumbnail.width, thumbnail.height)
            self.photo = ImageTk.PhotoImage(thumbnail, master=self.canvas)
            self.canvas.create_image(x, y, image=self.photo, anchor="nw")
            thumbnail.close()
            self.image_var.set(f"{self.active + 1}/{len(self.attachments)} · {attachment.image.width} × {attachment.image.height} px")
        self.update_image_controls()

    def start_selection(self, event):
        if self.displayed is None or self.busy:
            return
        self.selection_start = (event.x, event.y)
        self.selection_end = None
        self.canvas.delete("selection")

    def drag_selection(self, event):
        if self.selection_start is None or self.busy:
            return
        self.selection_end = (event.x, event.y)
        x, y, width, height = self.displayed
        x1, y1 = self.selection_start
        clamp_x = lambda value: max(x, min(x + width, value))
        clamp_y = lambda value: max(y, min(y + height, value))
        self.canvas.delete("selection")
        self.canvas.create_rectangle(clamp_x(x1), clamp_y(y1), clamp_x(event.x), clamp_y(event.y),
                                      outline=ACCENT, width=2, dash=(5, 3), tags="selection")
        self.update_image_controls()

    def cancel_selection(self):
        self.selection_start = self.selection_end = None
        self.canvas.delete("selection")
        self.update_image_controls()

    def crop_selected(self):
        if self.busy or self.active is None or self.selection_end is None:
            return
        try:
            attachment = self.attachments[self.active]
            box = selection_to_box(self.selection_start, self.selection_end, self.displayed, attachment.image.size)
            attachment.crop(box)
            self.render_preview()
            self.status("Recorte aplicado a la copia de trabajo. «Restaurar» recupera la imagen completa.")
        except ValueError as exc:
            self.status(str(exc), error=True)

    def restore_image(self):
        if self.active is not None and not self.busy:
            self.attachments[self.active].restore()
            self.render_preview()
            self.status("Imagen completa restaurada.")

    def names_changed(self, _=None):
        if not self.names.edit_modified():
            return
        self.names.edit_modified(False)
        if not self.busy and self.names.get("1.0", "end").strip() != self.synced_text:
            if self.searched_queries:
                self.clear_results()
                self.status("Cambiaste los nombres. Vuelve a buscar para elegir las nuevas coincidencias.")
            if self.table_timer is not None:
                self.after_cancel(self.table_timer)
            self.table_timer = self.after(220, self.sync_table_from_text)

    def sync_table_from_text(self, invalidate=True):
        if self.table_timer is not None:
            self.after_cancel(self.table_timer)
            self.table_timer = None
        text = self.names.get("1.0", "end").strip()
        if text != self.synced_text:
            if invalidate and self.searched_queries:
                self.clear_results()
            parsed = parse_exported_playlist(text)
            if parsed is not None:
                self.songs.set_imported(parsed.songs)
                self.import_summary = f"Lista por bloques: {len(parsed.songs)} canciones · {parsed.timed_blocks} duraciones."
                if parsed.warnings:
                    self.import_summary += " Hay bloques para revisar."
                if text != self.last_pasted_export:
                    self.raw_text.configure(state="normal")
                    if self.raw_text.get("1.0", "end").strip():
                        self.raw_text.insert("end", "\n\n")
                    self.raw_text.insert("end", "Texto pegado original\n" + "─" * 20 + "\n" + text)
                    self.raw_text.configure(state="disabled")
                    self.last_pasted_export = text
                self.status(self.import_summary)
            else:
                self.songs.set_queries(clean_queries(text, enforce_limit=False), self.query_sources, self.query_uploaders)
                self.import_summary = ""
            self.synced_text = text
            self.update_report()
        self.names.edit_modified(False)

    def on_table_changed(self):
        self.clear_results()
        if self.table_timer is not None:
            self.after_cancel(self.table_timer)
            self.table_timer = None
        text = "\n".join(self.songs.queries())
        self.names.edit_separator()
        self.names.configure(autoseparators=False)
        self.names.delete("1.0", "end")
        self.names.insert("1.0", text)
        self.names.edit_separator()
        self.names.configure(autoseparators=True)
        self.names.edit_modified(False)
        self.synced_text = text
        self.import_summary = ""
        self.status("Tabla actualizada. Busca las canciones marcadas cuando termines de revisarlas.")

    def on_tab_changed(self, _=None):
        if hasattr(self, "songs") and self.tabs.select() == str(self.table_tab) and not self.busy:
            self.sync_table_from_text()

    def review_table(self):
        if self.busy:
            return
        self.sync_table_from_text()
        self.tabs.select(self.table_tab)
        self.status((self.import_summary + " " if self.import_summary else "") + "Revisa la tabla y marca las canciones que quieras buscar.")

    def clean_playlist_text(self):
        if self.busy:
            return
        text = self.names.get("1.0", "end").strip()
        if not text:
            self.status("Pega primero el texto de la lista o lee una imagen.", error=True)
            return
        if parse_exported_playlist(text) is not None:
            self.review_table()
            return
        lines = organize_playlist_text(text, uploaders=self.query_uploaders)
        self.clear_results()
        self.names.edit_separator()
        self.names.configure(autoseparators=False)
        self.names.delete("1.0", "end")
        self.names.insert("1.0", "\n".join(lines))
        self.names.edit_separator()
        self.names.configure(autoseparators=True)
        self.sync_table_from_text()
        self.status(f"Lista organizada: {len(lines)} entradas. Revisa títulos incompletos antes de buscar. Ctrl + Z deshace la limpieza.")

    def set_busy(self, busy):
        self.busy = busy
        for widget in self.controls:
            widget.configure(state="disabled" if busy else "normal")
        self.image_list.configure(state="disabled" if busy else "normal")
        self.names.configure(state="disabled" if busy else "normal")
        self.songs.set_enabled(not busy)
        self.cancel_button.configure(state="normal" if busy else "disabled", text="Cancelar operación")
        self.update_image_controls()
        self.update_choice_count()
        self.retry_button.configure(state="normal" if not busy and self.pending_indices(retryable=True) else "disabled")

    def start_job(self, config, images=()):
        if self.busy:
            return
        self.errors.clear()
        self.task = config["task"]
        self.job = ImportJob()
        self.set_busy(True)
        self.progress.configure(value=0, mode="indeterminate")
        self.progress.start(15)
        threading.Thread(target=self.job.run, args=(config, images), daemon=True).start()

    def start_ocr(self):
        if not self.attachments or self.busy:
            return
        self.clear_results()
        self.status("Preparando OCR local. La primera lectura puede tardar unos segundos.")
        images = [(attachment.name, attachment.image.copy()) for attachment in self.attachments]
        self.start_job(dict(task="ocr"), images)

    def start_search(self):
        if self.busy:
            return
        try:
            self.songs.commit_editor()
            self.sync_table_from_text()
            queries = clean_queries("\n".join(self.songs.queries(checked_only=True)))
            source_url = playlist_url(self.playlist_var.get())
            if not queries:
                raise ValueError("Marca al menos una canción en la tabla para buscarla.")
        except ValueError as exc:
            self.status(str(exc), error=True)
            return
        self.clear_results()
        self.searched_queries = queries
        groups = {query.casefold(): [] for query in queries}
        for item, entry in self.songs.entries():
            normalized = clean_queries(entry.query, enforce_limit=False)
            if entry.checked and normalized and normalized[0].casefold() in groups:
                groups[normalized[0].casefold()].append(item)
        self.search_row_groups = [groups[query.casefold()] for query in queries]
        self.search_row_ids = [group[0] for group in self.search_row_groups]
        for index in range(len(self.search_row_ids)):
            self.set_search_state(index, "En cola")
        self.tabs.select(self.search_tab)
        self.status("Buscando coincidencias por nombre en YouTube…")
        self.playlist_report = None
        self.playlist_error = ""
        self.start_job(dict(task="search", queries=queries, cookies=self.cookies, playlist_url=source_url))

    def clear_results(self):
        self.inline_audio.stop()
        self.stop_preview()
        self.results.delete(*self.result_groups)
        self.result_groups.clear()
        self.search_outcomes.clear()
        self.query_errors.clear()
        self.transfer_report = None
        self.selected_candidates.clear()
        self.candidates.clear()
        self.searched_queries = []
        self.search_row_ids = []
        self.search_row_groups = []
        self.result_counts.clear()
        if hasattr(self, "songs"):
            self.songs.reset_states()
        if hasattr(self, "add_button"):
            self.update_choice_count()

    def add_candidates(self, event):
        index = event["index"]
        self.search_outcomes[index] = event
        parent = self.results.insert("", "end", text=event["query"], open=True, tags=("query",))
        self.result_groups[parent] = event["query"]
        items = []
        for candidate in event["candidates"]:
            item = self.results.insert(parent, "end", text=candidate["title"],
                                       values=(candidate["channel"], duration_label(candidate["duration"]), ""))
            self.candidates[item] = (index, candidate)
            items.append(item)
        if not event["candidates"]:
            self.results.insert(parent, "end", text=("Error: " if event.get("failed") else "Sin resultados: ") +
                                (event.get("reason") or self.query_errors.get(index) or "Revisa el nombre o vuelve a buscar."))
        if index < len(self.search_row_ids):
            row = self.search_row_ids[index]
            count = len(event["candidates"])
            self.result_counts[row] = count
            self.set_search_state(index, "Error" if event.get("failed") else f"{count} {'resultado' if count == 1 else 'resultados'}" if count else "Sin resultados")
        metadata = {}
        entry = None
        if index < len(self.search_row_ids):
            entry = self.songs.items.get(self.search_row_ids[index])
            if entry:
                metadata = dict(title=entry.title, artist=entry.artist, duration=entry.duration)
        match = best_candidate(event["query"], event["candidates"], **metadata)
        if match is not None and index not in self.selected_candidates:
            position, comparison = match
            review_reason = (entry.review_reason if entry else "") or comparison.review_reason
            if comparison.auto_select and not review_reason:
                self.select_candidate(items[position], label="✓ Auto · " + ("exacta" if comparison.exact else "similar"))
            else:
                event["auto_review_reason"] = review_reason + " Revisa las alternativas y elige una manualmente."
                self.results.set(items[position], "chosen", "Revisar · sin marcar")
                if index < len(self.search_row_ids):
                    self.set_search_state(index, "Revisar coincidencia")
                self.update_report()
        self.filter_results()

    def filter_results(self):
        # Mantiene todas las alternativas del grupo para poder compararlas.
        for parent, query in self.result_groups.items():
            children = self.results.get_children(parent)
            matches = self.results_filter.matches(query) or any(
                self.results_filter.matches(query, self.results.item(child, "text"),
                                            self.results.set(child, "channel")) for child in children)
            if matches:
                self.results.move(parent, "", "end")
            else:
                self.results.selection_remove(parent, *children)
                self.results.detach(parent)
        self.inline_audio.schedule()

    def choose_result(self, _=None):
        if self.busy:
            return
        selected = self.results.selection()
        if not selected or selected[0] not in self.candidates:
            return
        self.select_candidate(selected[0], toggle=True)

    def select_candidate(self, item, *, label="✓ Elegida", toggle=False):
        """Única ruta de selección para propuestas automáticas y cambios manuales."""
        index, _ = self.candidates[item]
        self.transfer_report = None
        previous = self.selected_candidates.pop(index, None)
        if previous:
            self.results.set(previous, "chosen", "")
            self.results.item(previous, tags=())
        if not toggle or previous != item:
            self.selected_candidates[index] = item
            self.results.set(item, "chosen", label)
            self.results.item(item, tags=("chosen",))
        if index < len(self.search_row_ids):
            row = self.search_row_ids[index]
            count = self.result_counts.get(row, 0)
            self.set_search_state(index, "Elegida" if index in self.selected_candidates else f"{count} {'resultado' if count == 1 else 'resultados'}")
        self.update_choice_count()

    def update_choice_count(self):
        count = len(self.selected_candidates)
        self.choice_var.set(f"{count} canci{'ón elegida' if count == 1 else 'ones elegidas'}")
        if hasattr(self, "add_button"):
            self.add_button.configure(state="normal" if count and not self.busy else "disabled")
        if not self.busy:
            self.update_report()

    def set_search_state(self, index, state):
        rows = self.search_row_groups[index] if index < len(self.search_row_groups) else [self.search_row_ids[index]]
        for item in rows:
            self.songs.set_state(item, state)

    def view_result(self):
        selected = self.results.selection()
        if selected and selected[0] in self.candidates:
            webbrowser.open(self.candidates[selected[0]][1]["url"])

    def update_preview_controls(self):
        selected = self.results.selection()
        valid = bool(selected and selected[0] in self.candidates and not self.closing)
        self.play_button.configure(state="normal" if valid else "disabled")
        video = self.player_job and not self.player_job.cancelled.is_set()
        audio = hasattr(self, "inline_audio") and self.inline_audio.job
        if hasattr(self, "stop_player_button"):
            self.stop_player_button.configure(state="normal" if video or audio else "disabled")

    def preview_result(self):
        selected = self.results.selection()
        if self.closing or not selected or selected[0] not in self.candidates:
            return
        self.inline_audio.stop()
        candidate = self.candidates[selected[0]][1]
        previous = self.player_job
        job = self.player_job = PlayerJob()
        self.player_failed = False
        self.player_status_var.set("Abriendo: " + candidate["title"])
        self.player_status_label.configure(foreground=MUTED)
        self.update_preview_controls()

        def start():
            if previous:
                previous.cancel()
            job.run(dict(url=candidate["url"], title=candidate["title"]))

        threading.Thread(target=start, daemon=True).start()

    def stop_preview(self):
        job = self.player_job
        if job:
            job.cancelled.set()
            threading.Thread(target=job.cancel, daemon=True).start()
            self.player_job = None
            self.player_status_var.set("Reproducción detenida.")
        if hasattr(self, "play_button"):
            self.update_preview_controls()

    def audio_status(self, text, error=False):
        self.player_status_var.set(text)
        self.player_status_label.configure(foreground=RED if error else MUTED)

    def stop_playback(self):
        self.inline_audio.stop()
        self.stop_preview()
        self.audio_status("Reproducción detenida.")

    def poll_player_events(self):
        if not self.player_job:
            return
        for _ in range(15):
            try:
                event = self.player_job.events.get_nowait()
            except queue.Empty:
                break
            if event["event"] == "player":
                state = event["status"]
                self.player_failed = state == "error"
                self.player_status_var.set(event.get("text") or {
                    "ready": "Reproductor listo. Usa Reproducir y la barra de tiempo en su ventana.",
                    "playing": "Reproduciendo. Puedes pausar, adelantar y retroceder en el reproductor.",
                    "paused": "Reproducción en pausa.", "ended": "Reproducción terminada.",
                    "autoplay_blocked": "Pulsa Reproducir en la ventana del reproductor para empezar.",
                }.get(state, "Abriendo reproductor…"))
                self.player_status_label.configure(foreground=RED if self.player_failed else MUTED)
            elif event["event"] == "player_done":
                if not self.player_failed:
                    self.player_status_var.set("Reproductor cerrado.")
                self.player_job = None
                self.update_preview_controls()
                break

    def add_selected(self):
        if self.busy or not self.selected_candidates:
            return
        try:
            self.sync_table_from_text(invalidate=False)
            if clean_queries("\n".join(self.songs.queries(checked_only=True))) != self.searched_queries:
                raise ValueError("Los nombres cambiaron. Busca de nuevo antes de añadir las canciones.")
        except ValueError as exc:
            self.status(str(exc), error=True)
            return
        try:
            records = [dict(query=self.searched_queries[index], title=self.candidates[item][1]["title"],
                            url=self.candidates[item][1]["url"])
                       for index, item in sorted(self.selected_candidates.items())]
            self.transfer_report = selection_transfer(records)
            self.update_report()
            report = self.transfer_report
            if report["repeated"]:
                self.tabs.select(self.report_tab)
                self.status(f"Atención: {report['selected']} elecciones corresponden a {report['unique']} videos únicos. Revisa los títulos que comparten enlace en el informe.", error=True)
                preview = transfer_text(report)
                if len(preview) > 1500:
                    preview = preview[:1500] + "\n…El detalle completo está en «Informe y pendientes»."
                if not messagebox.askyesno("Hay elecciones con el mismo enlace", preview +
                    f"\n\n¿Añadir {report['unique']} videos únicos?\nElige No para revisar o cambiar las coincidencias.",
                    parent=self, icon="warning", default="no"):
                    return
            if self.on_add(report["urls"]) is False:
                self.status("No se añadieron los enlaces a la cola. Comprueba si hay una descarga activa; tus elecciones se conservan.", error=True)
                return
        except Exception as exc:
            self.errors.append(f"No se pudieron añadir las elecciones: {exc}")
            self.update_report()
            self.tabs.select(self.report_tab)
            self.status("No se pudo completar el paso a descargas. Tus elecciones se conservan; consulta el informe.", error=True)
            return
        if self.on_transfer:
            self.on_transfer(dict(report, source_report=self.report_text.get("1.0", "end-1c")))
        self.close()

    def cancel_job(self):
        if self.job is None or not self.busy or self.job.cancelled.is_set():
            return
        self.status("Cancelando la operación…")
        self.cancel_button.configure(state="disabled", text="Cancelando…")
        threading.Thread(target=self.job.cancel, daemon=True).start()

    def handle_event(self, event):
        kind = event["event"]
        cancelled = self.job is not None and self.job.cancelled.is_set()
        if kind == "import_status" and not cancelled:
            self.status(event["text"])
            index = event.get("query_index")
            if index is not None and index < len(self.search_row_ids):
                self.set_search_state(index, "Buscando…")
        elif kind == "import_error":
            self.errors.append(event["text"])
            if "query_index" in event:
                self.query_errors[event["query_index"]] = event["text"]
        elif kind == "playlist_report" and not cancelled:
            self.playlist_report = event["report"]
            self.playlist_error = ""
        elif kind == "playlist_error" and not cancelled:
            self.playlist_error = event["text"]
            self.errors.append("Playlist: " + event["text"])
        elif kind == "attachment_result":
            if cancelled:
                event["attachment"].close()
            else:
                self.attachments.append(event["attachment"])
                self.refresh_attachments(len(self.attachments) - 1)
                self.update_progress(event["index"], event["total"])
        elif kind == "ocr_result" and not cancelled:
            self.query_uploaders.update(event.get("uploaders", {}))
            current = self.names.get("1.0", "end").strip()
            # El editor está deshabilitado durante el trabajo; solo el hilo Tk lo actualiza.
            self.names.configure(state="normal")
            combined = clean_queries(current + "\n" + "\n".join(event["lines"]), enforce_limit=False)
            self.names.delete("1.0", "end")
            self.names.insert("1.0", "\n".join(combined))
            self.names.edit_modified(False)
            self.names.configure(state="disabled")
            for query in event["lines"]:
                self.query_sources.setdefault(query.casefold(), event["name"])
            self.raw_text.configure(state="normal")
            if self.raw_text.get("1.0", "end").strip():
                self.raw_text.insert("end", "\n\n")
            self.raw_text.insert("end", f"{event['name']}\n{'─' * 20}\n" + event.get("raw_text", "\n".join(event["lines"])))
            self.raw_text.configure(state="disabled")
            self.sync_table_from_text()
            self.update_progress(event["index"], event["total"])
        elif kind == "search_result" and not cancelled:
            self.add_candidates(event)
            self.update_progress(event.get("progress_index", event["index"] + 1), event["total"])
        elif kind == "job_done":
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0 if event["cancelled"] else 100)
            self.set_busy(False)
            if self.task == "search":
                for row in (item for group in self.search_row_groups for item in group):
                    entry = self.songs.items.get(row)
                    if entry and entry.state in ("En cola", "Buscando…"):
                        self.songs.set_state(row, "Cancelada" if event["cancelled"] else "Error")
            self.update_report()
            if self.task == "search" and self.searched_queries:
                pending = self.pending_indices()
                failures = sum(bool(outcome.get("failed")) for outcome in self.search_outcomes.values())
                empty = sum(not outcome.get("candidates") and not outcome.get("failed") for outcome in self.search_outcomes.values())
                missing = sum(index not in self.search_outcomes for index in range(len(self.searched_queries)))
                manual = sum(bool(self.search_outcomes.get(index, {}).get("candidates")) for index in pending)
                unavailable = len(self.playlist_report["unavailable"]) if self.playlist_report else 0
                problem = bool(pending or self.errors or unavailable or (self.playlist_report or {}).get("unaccounted"))
                summary = f"{'Búsqueda cancelada' if event['cancelled'] else 'Búsqueda terminada'}: {len(self.searched_queries)} consultas · {len(self.selected_candidates)} elegidas · {len(pending)} pendientes ({empty} sin resultados, {failures} errores, {missing} sin completar, {manual} sin elegir)."
                if self.playlist_report:
                    summary += f" Playlist original: {self.playlist_report['total']} entradas; {unavailable} no disponibles."
                if problem:
                    self.tabs.select(self.report_tab)
                    self.status(summary + " Revisa «Informe y pendientes» para ver nombres y motivos.", error=True)
                else:
                    self.status(summary + " Puedes revisar o cambiar las elecciones con doble clic.")
                return
            if self.task == "playlist":
                self.tabs.select(self.report_tab)
                if self.playlist_report:
                    report = self.playlist_report
                    self.status(f"Playlist comprobada: {report['total']} entradas · {report['readable']} con título · {len(report['unavailable'])} no disponibles. Consulta el informe.",
                                error=bool(report["unavailable"] or report.get("unaccounted")))
                else:
                    self.status("Comprobación cancelada." if event["cancelled"] else "No se pudo comprobar la playlist. Consulta el informe.", error=True)
                return
            if event["cancelled"]:
                self.status("Operación cancelada. Puedes continuar con los resultados que ya llegaron.")
            elif self.errors:
                self.status("Algunos elementos fallaron. " + " | ".join(self.errors[:2]), error=True)
            elif self.task == "load":
                self.status("Imágenes cargadas. Arrastra para recortar o pulsa «Leer imágenes → texto».")
            elif self.task == "ocr":
                if self.names.get("1.0", "end").strip():
                    self.tabs.select(self.table_tab)
                    self.status("Tabla creada. Revisa artista y título, marca las canciones y busca coincidencias.")
                else:
                    self.status("No se encontró texto. Prueba con un recorte más claro o escribe los nombres.", error=True)
            elif not self.candidates:
                self.status("No se encontraron coincidencias. Edita los nombres y vuelve a buscar.")
            else:
                self.status(f"Resultados listos: {self.choice_var.get()} automáticamente. Revisa las opciones; puedes cambiarlas o quitarlas con doble clic.")

    def update_progress(self, index, total):
        self.progress.stop()
        self.progress.configure(mode="determinate", value=index / max(1, total) * 100)

    def poll_events(self):
        self.poll_timer = None
        self.poll_player_events()
        self.inline_audio.poll()
        if self.job is not None:
            for _ in range(30):
                try:
                    event = self.job.events.get_nowait()
                except queue.Empty:
                    break
                try:
                    self.handle_event(event)
                except Exception as exc:
                    reason = f"No se pudo procesar una respuesta del trabajador: {type(exc).__name__}: {exc}"
                    self.errors.append(reason)
                    index = event.get("index") if isinstance(event, dict) else None
                    if isinstance(index, int) and 0 <= index < len(self.searched_queries):
                        self.query_errors[index] = reason
                        self.remove_query_results(index)
                        self.add_candidates(dict(index=index, query=self.searched_queries[index], candidates=[],
                                                 failed=True, reason=reason))
        if self.closing and not self.busy:
            self.destroy()
            return
        self.poll_timer = self.after(60, self.poll_events)

    def close(self):
        self.inline_audio.stop()
        self.stop_preview()
        if self.busy:
            self.closing = True
            self.cancel_job()
        else:
            self.destroy()

    def destroy(self):
        self.inline_audio.destroy()
        self.stop_preview()
        for timer in (self.poll_timer, self.render_timer, self.table_timer):
            if timer is not None:
                self.after_cancel(timer)
        self.poll_timer = self.render_timer = self.table_timer = None
        self.photo = None
        for attachment in self.attachments:
            attachment.close()
        self.attachments.clear()
        if self.grab_current() is self:
            self.grab_release()
        super().destroy()
        self.controls.clear()
        for name, value in list(vars(self).items()):
            if isinstance(value, (tk.Variable, tk.Misc)):
                delattr(self, name)
