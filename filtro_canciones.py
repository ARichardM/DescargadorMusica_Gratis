"""Filtro local reutilizable: no modifica canciones ni realiza consultas de red."""

import tkinter as tk
from tkinter import ttk

from coincidencias import normalize


class SongFilter(ttk.Frame):
    def __init__(self, master, on_change):
        super().__init__(master, style="Card.TFrame")
        self.value = tk.StringVar(master=self)
        ttk.Label(self, text="Buscar en la lista:", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        self.entry = ttk.Entry(self, textvariable=self.value)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Escape>", lambda _: self.clear())
        ttk.Button(self, text="Limpiar", command=self.clear).pack(side="left", padx=(8, 0))
        self.trace = self.value.trace_add("write", lambda *_: on_change())

    def matches(self, *texts):
        haystack = normalize(" ".join(str(text or "") for text in texts))
        return all(word in haystack for word in normalize(self.value.get()).split())

    def clear(self):
        self.value.set("")
        return "break"

    def destroy(self):
        self.value.trace_remove("write", self.trace)
        super().destroy()
        del self.value
