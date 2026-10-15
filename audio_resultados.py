"""Controles de audio junto a las filas visibles, sin crear widgets por toda la lista."""

import queue
import threading
import tkinter as tk
from tkinter import ttk

from interfaz import ACCENT, MUTED, SURFACE
from reproductor_audio import AudioJob


def clock(seconds):
    seconds = max(0, int(seconds or 0))
    return f"{seconds // 60}:{seconds % 60:02d}"


class AudioRow(tk.Frame):
    def __init__(self, owner):
        super().__init__(owner.tree, bg=SURFACE)
        self.owner, self.item, self.dragging = owner, None, False
        self.button = tk.Button(self, text="▶", width=3, bd=0, bg=SURFACE, fg=ACCENT,
            activebackground="#eeebff", cursor="hand2", font=("Segoe UI", 10),
            command=lambda: owner.toggle(self.item), takefocus=True)
        self.button.pack(side="left")
        self.time = tk.Label(self, text="0:00 / 0:00", bg=SURFACE, fg=MUTED, font=("Segoe UI", 8), width=11)
        self.time.pack(side="right", padx=(2, 4))
        self.scale = ttk.Scale(self, from_=0, to=1, command=self.scrub)
        self.scale.pack(side="left", fill="x", expand=True, padx=3)
        self.scale.bind("<ButtonPress-1>", self.begin)
        self.scale.bind("<B1-Motion>", self.drag)
        self.scale.bind("<ButtonRelease-1>", self.release)
        self.scale.bind("<KeyRelease>", self.seek_keyboard)

    def begin(self, event):
        self.dragging = self.owner.item == self.item and bool(self.owner.duration)
        if self.dragging:
            self.drag(event)
            return "break"

    def drag(self, event):
        if self.dragging:
            fraction = min(1, max(0, (event.x - 7) / max(1, self.scale.winfo_width() - 14)))
            self.scale.set(fraction * self.owner.duration)
            return "break"

    def scrub(self, value):
        if self.dragging:
            self.time.configure(text=f"{clock(float(value))} / {clock(self.owner.duration)}")

    def release(self, _):
        if self.dragging:
            self.owner.seek(self.item, self.scale.get())
        self.dragging = False

    def seek_keyboard(self, event):
        if event.keysym in ("Left", "Right", "Home", "End", "Prior", "Next"):
            self.owner.seek(self.item, self.scale.get())

    def update_state(self):
        active = self.item == self.owner.item
        duration = self.owner.duration if active else self.owner.candidates[self.item][1].get("duration") or 0
        position = self.owner.position if active else 0
        state = self.owner.state if active else "idle"
        self.button.configure(text="Ⅱ" if active and self.owner.job and not self.owner.paused else "▶")
        self.scale.configure(to=max(1, duration), state="normal" if active and duration and self.owner.job else "disabled")
        if not self.dragging:
            self.scale.set(position)
            self.time.configure(text=("Cargando…" if state == "loading" else
                                      f"{clock(position)} / {clock(duration)}"))


class InlineAudio:
    def __init__(self, tree, candidates, *, cookies, before_play, status, changed):
        self.tree, self.candidates, self.cookies = tree, candidates, cookies
        self.before_play, self.status, self.changed = before_play, status, changed
        self.job = self.item = None
        self.state = "idle"
        self.paused = False
        self.position = self.duration = 0
        self.rows = []
        self.timer = None
        self.closed = False
        tree.bind("<Configure>", self.resize, add="+")
        for event in ("<Map>", "<<TreeviewOpen>>", "<<TreeviewClose>>", "<ButtonRelease-1>"):
            tree.bind(event, self.schedule, add="+")

    def resize(self, _=None):
        fixed = sum(self.tree.column(column, "width") for column in ("duration", "chosen", "audio"))
        available = max(220, self.tree.winfo_width() - fixed - 4)
        title = max(150, int(available * 0.70))
        self.tree.column("#0", width=title)
        self.tree.column("channel", width=max(70, available - title))
        self.schedule()

    def schedule(self, _=None):
        if not self.closed and self.timer is None:
            self.timer = self.tree.after_idle(self.refresh)

    def refresh(self):
        self.timer = None
        if self.closed:
            return
        visible = []
        seen = set()
        if self.tree.winfo_ismapped():
            # Muestreo de las coordenadas visibles: coste independiente del tamaño de la lista.
            for y in range(0, self.tree.winfo_height(), 8):
                item = self.tree.identify_row(y)
                if item in seen or item not in self.candidates:
                    continue
                seen.add(item)
                box = self.tree.bbox(item, "audio")
                if box and box[0] + box[2] <= self.tree.winfo_width():
                    visible.append((item, box))
        while len(self.rows) < len(visible):
            self.rows.append(AudioRow(self))
        for index, row in enumerate(self.rows):
            if index >= len(visible):
                row.place_forget()
                row.item = None
                row.dragging = False
                continue
            item, (x, y, width, height) = visible[index]
            if row.item != item:
                row.dragging = False
            row.item = item
            row.place(x=x + 1, y=y + 1, width=max(1, width - 2), height=max(1, height - 2))
            row.update_state()

    def toggle(self, item):
        if self.closed or item not in self.candidates:
            return
        if item == self.item and self.job:
            self.paused = not self.paused
            self.job.command("pause" if self.paused else "resume")
            self.state = "paused" if self.paused else "loading"
        else:
            previous = self.job
            if previous:
                previous.cancelled.set()
            self.before_play()
            candidate = self.candidates[item][1]
            job = self.job = AudioJob()
            self.item, self.state = item, "loading"
            self.paused = False
            self.position, self.duration = 0, candidate.get("duration") or 0
            cookies = self.cookies

            def start():
                if previous:
                    previous.cancel()
                job.run(dict(url=candidate["url"], duration=candidate.get("duration"), cookies=cookies))

            threading.Thread(target=start, daemon=True).start()
        self.status("Audio: " + self.candidates[item][1]["title"] + (" · En pausa" if self.state == "paused" else ""))
        self.changed()
        self.schedule()

    def seek(self, item, position):
        if item == self.item and self.job and self.duration:
            self.position = min(max(0, float(position)), self.duration)
            self.job.command("seek", position=self.position)

    def poll(self):
        if not self.job:
            return
        updated = False
        for _ in range(20):
            try:
                event = self.job.events.get_nowait()
            except queue.Empty:
                break
            updated = True
            if event["event"] == "audio_done":
                self.job = None
                if self.state not in ("error", "ended"):
                    self.state = "idle"
                self.changed()
                break
            self.state = event["status"]
            if self.paused and self.state in ("playing", "loading"):
                self.state = "paused"
            self.position = event.get("position", self.position)
            self.duration = event.get("duration", self.duration)
            if self.state == "error":
                self.status(event.get("text") or "No se pudo abrir el audio.", error=True)
            elif self.state == "ended":
                self.status("Audio terminado. Pulsa ▶ para volver a escucharlo.")
        if updated:
            self.schedule()

    def stop(self):
        job, self.job = self.job, None
        self.item, self.state, self.position, self.duration = None, "idle", 0, 0
        self.paused = False
        if job:
            job.cancelled.set()
            threading.Thread(target=job.cancel, daemon=True).start()
        self.schedule()
        self.changed()

    def remove(self, item):
        if item == self.item:
            self.stop()
        self.schedule()

    def destroy(self):
        self.stop()
        self.closed = True
        if self.timer is not None:
            self.tree.after_cancel(self.timer)
            self.timer = None
        for row in self.rows:
            row.destroy()
        self.rows.clear()
