"""Consulta paginada del historial sin hacer operaciones de disco en el hilo Tk."""

from datetime import datetime
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk

from historial import DownloadHistory, PAGE_SIZE


class HistoryPanel(ttk.Frame):
    def __init__(self, master, path, open_path, add_urls, can_add, expand=None):
        super().__init__(master, style="Card.TFrame", padding=(0, 8, 0, 0))
        self.store = DownloadHistory(path)
        self.open_path, self.add_urls, self.can_add = open_path, add_urls, can_add
        self.events = queue.Queue()
        self.generation = self.offset = 0
        self.total = 0
        self.records = {}
        self.closed = False
        self.refresh_timer = self.poll_timer = None
        self.search_var = tk.StringVar(master=self)
        self.status_var = tk.StringVar(master=self, value="Todavía no hay descargas guardadas.")

        search = ttk.Frame(self, style="Card.TFrame")
        search.pack(fill="x", pady=(0, 6))
        self.search_entry = ttk.Entry(search, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda _: self.search())
        ttk.Button(search, text="Buscar", command=self.search).pack(side="left", padx=(6, 0))
        ttk.Button(search, text="Todos", command=self.show_all).pack(side="left", padx=(4, 0))
        if expand:
            ttk.Button(search, text="Ampliar", command=expand).pack(side="left", padx=(4, 0))

        actions = ttk.Frame(self, style="Card.TFrame")
        actions.pack(side="bottom", fill="x", pady=(6, 0))
        self.open_button = ttk.Button(actions, text="Abrir", command=self.open_selected)
        self.open_button.pack(side="left")
        self.folder_button = ttk.Button(actions, text="Carpeta", command=lambda: self.open_selected(folder=True))
        self.folder_button.pack(side="left", padx=4)
        self.queue_button = ttk.Button(actions, text="A la cola", command=self.add_selected)
        self.queue_button.pack(side="left")
        self.next_button = ttk.Button(actions, text="›", width=3, command=lambda: self.move_page(1))
        self.next_button.pack(side="right")
        self.previous_button = ttk.Button(actions, text="‹", width=3, command=lambda: self.move_page(-1))
        self.previous_button.pack(side="right", padx=4)
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel",
                  wraplength=410, font=("Segoe UI", 9)).pack(side="bottom", anchor="w", pady=(6, 0))

        table = ttk.Frame(self, style="Card.TFrame")
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("date", "title", "format", "state"),
                                 show="headings", selectmode="browse", height=3)
        for column, title, width in (("date", "FECHA", 112), ("title", "CANCIÓN / VIDEO", 180),
                                     ("format", "TIPO", 48), ("state", "ESTADO", 72)):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, minwidth=width if column != "title" else 80,
                             stretch=column == "title")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _: self.open_selected())
        self.tree.bind("<Return>", lambda _: self.open_selected())
        self.tree.bind("<<TreeviewSelect>>", lambda _: self.update_actions())
        self.update_actions()
        self.refresh()
        self.poll_timer = self.after(60, self.poll)

    def search(self):
        self.offset = 0
        self.refresh()

    def show_all(self):
        self.search_var.set("")
        self.search()

    def move_page(self, direction):
        self.offset = max(0, self.offset + direction * PAGE_SIZE)
        self.refresh()

    def schedule_refresh(self):
        if self.refresh_timer is None and not self.closed:
            self.refresh_timer = self.after(200, self.refresh)

    def refresh(self):
        if self.closed:
            return
        if self.refresh_timer is not None:
            self.after_cancel(self.refresh_timer)
            self.refresh_timer = None
        self.generation += 1
        generation, search, offset = self.generation, self.search_var.get(), self.offset

        def read():
            try:
                rows, total = self.store.page(search, offset)
                self.events.put((generation, rows, total, ""))
            except Exception as exc:
                self.events.put((generation, [], 0, str(exc)))

        threading.Thread(target=read, daemon=True).start()

    def poll(self):
        self.poll_timer = None
        for _ in range(20):
            try:
                generation, rows, total, error = self.events.get_nowait()
            except queue.Empty:
                break
            if generation != self.generation:
                continue
            if error:
                self.status_var.set("No se pudo leer el historial. " + error)
                continue
            selected = self.tree.selection()
            children = self.tree.get_children()
            if children:
                self.tree.delete(*children)
            self.records = {str(row["id"]): row for row in rows}
            for key, row in self.records.items():
                date = datetime.fromisoformat(row["created_at"]).astimezone().strftime("%d/%m/%y %H:%M")
                title = row["title"] + (f" · {row['artist']}" if row["artist"] else "")
                state = "Existente" if row["state"] == "existing" else "Guardado"
                self.tree.insert("", "end", iid=key, values=(date, title, row["format"], state))
            if selected and selected[0] in self.records:
                self.tree.selection_set(selected[0])
            self.total = total
            self.status_var.set(f"{self.offset + 1}–{self.offset + len(rows)} de {total} registros"
                                if rows else "Sin resultados." if self.search_var.get().strip()
                                else "Todavía no hay descargas guardadas.")
            self.update_actions()
        if not self.closed:
            self.poll_timer = self.after(60, self.poll)

    def selected_record(self):
        selected = self.tree.selection()
        return self.records.get(selected[0]) if selected else None

    def update_actions(self):
        record = self.selected_record() if hasattr(self, "tree") else None
        for button in (self.open_button, self.folder_button):
            button.configure(state="normal" if record else "disabled")
        self.queue_button.configure(state="normal" if record and record["source_url"] and self.can_add() else "disabled")
        self.previous_button.configure(state="normal" if self.offset else "disabled")
        self.next_button.configure(state="normal" if self.offset + PAGE_SIZE < self.total else "disabled")

    def open_selected(self, folder=False):
        record = self.selected_record()
        if not record:
            return
        path = Path(record["filename"])
        path = path.parent if folder else path
        if not path.exists():
            self.status_var.set("El archivo o la carpeta ya no existe en esa ubicación.")
            return
        self.open_path(path)

    def add_selected(self):
        record = self.selected_record()
        if record and record["source_url"] and self.can_add():
            self.add_urls([record["source_url"]])

    def destroy(self):
        self.closed = True
        for timer in (self.refresh_timer, self.poll_timer):
            if timer is not None:
                self.after_cancel(timer)
        super().destroy()
