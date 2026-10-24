"""Audio por resultado: acciones independientes, controles visibles y limpieza."""

import gc
import queue
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import descargador_gui as app
from importar_canciones import ImportSongsDialog


def fake_audio():
    cancelled = threading.Event()
    return SimpleNamespace(events=queue.Queue(), cancelled=cancelled, run=Mock(), command=Mock(),
                           cancel=Mock(side_effect=cancelled.set))


class InlineAudioTests(unittest.TestCase):
    def setUp(self):
        self.root = app.launch_gui()
        self.received = []
        self.dialog = ImportSongsDialog(self.root, self.received.extend)
        self.dialog.geometry("900x650")
        self.dialog.tabs.select(self.dialog.search_tab)
        self.dialog.add_candidates(dict(index=0, query="Artista - Canción", candidates=[
            dict(title="Oficial", channel="Artista", duration=180, url="https://youtu.be/abcdefghijk"),
            dict(title="Alternativa", channel="Artista", duration=170, url="https://youtu.be/lmnopqrstuv")]))
        self.rows = list(self.dialog.candidates)
        self.audio = self.dialog.inline_audio
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.audio = self.dialog = self.root = None
        gc.collect()

    def wait_for(self, condition):
        deadline = time.monotonic() + 4
        while not condition():
            self.assertLess(time.monotonic(), deadline)
            self.root.update()
            time.sleep(0.01)

    def start(self, item=None):
        job = fake_audio()
        with patch("audio_resultados.AudioJob", return_value=job):
            self.audio.toggle(item or self.rows[0])
            self.wait_for(lambda: job.run.called)
        return job

    def test_inline_play_pause_and_seek_keep_choices_even_while_searching(self):
        choices = dict(self.dialog.selected_candidates)
        self.dialog.set_busy(True)
        job = self.start()
        self.audio.toggle(self.rows[0])
        job.command.assert_called_with("pause")
        self.audio.seek(self.rows[0], 90)
        job.command.assert_called_with("seek", position=90)
        self.audio.toggle(self.rows[0])
        job.command.assert_called_with("resume")
        self.assertEqual(self.dialog.selected_candidates, choices)
        self.assertFalse(self.received)
        self.assertFalse(self.root.running)
        self.dialog.set_busy(False)

    def test_controls_are_beside_both_results_and_fit_compact_window(self):
        self.assertEqual({r.item for r in self.audio.rows if r.winfo_ismapped()}, set(self.rows))
        for row in self.audio.rows:
            self.assertGreater(row.winfo_width(), 200)
            self.assertLessEqual(row.winfo_x() + row.winfo_width(), self.dialog.results.winfo_width())
            self.assertEqual(str(row.scale["state"]), "disabled")
        self.assertTrue(self.dialog.play_button.winfo_ismapped())

    def test_switching_track_video_and_closing_stops_previous_audio(self):
        first = self.start()
        second = self.start(self.rows[1])
        self.wait_for(lambda: first.cancel.called)
        video = SimpleNamespace(events=queue.Queue(), cancelled=threading.Event(), run=Mock(), cancel=Mock())
        self.dialog.results.selection_set(self.rows[0])
        with patch("importar_canciones.PlayerJob", return_value=video):
            self.dialog.preview_result()
            self.wait_for(lambda: video.run.called)
        self.wait_for(lambda: second.cancel.called)
        third = self.start()
        self.wait_for(lambda: video.cancel.called)
        self.dialog.close()
        self.wait_for(lambda: third.cancel.called)

    def test_progress_drag_seeks_only_once_on_release(self):
        job = self.start()
        job.events.put(dict(event="audio", status="playing", position=30, duration=180))
        self.audio.poll()
        self.root.update()
        row = next(r for r in self.audio.rows if r.item == self.rows[0])
        self.assertAlmostEqual(row.scale.get(), 30)
        self.assertIn("0:30", row.time["text"])
        row.begin(SimpleNamespace(x=row.scale.winfo_width() // 2))
        row.drag(SimpleNamespace(x=row.scale.winfo_width() * 3 // 4))
        job.command.assert_not_called()
        # El progreso entrante no debe mover la barra que el usuario arrastra.
        target = row.scale.get()
        self.audio.position = 35
        row.update_state()
        self.assertAlmostEqual(row.scale.get(), target)
        row.release(None)
        job.command.assert_called_once_with("seek", position=target)

    def test_filter_scroll_and_collapse_recycle_only_visible_row_controls(self):
        for index in range(1, 100):
            self.dialog.add_candidates(dict(index=index, query=f"Grupo {index}", candidates=[
                dict(title=f"Canción {index}", channel="Canal", duration=60, url="https://youtu.be/abcdefghijk")]))
        self.root.update()
        self.assertLess(len(self.audio.rows), 25)
        self.dialog.results.yview_moveto(1)
        self.root.update()
        visible = {r.item for r in self.audio.rows if r.winfo_ismapped()}
        self.assertTrue(visible)
        self.assertFalse(set(self.rows) & visible)
        for row in self.audio.rows:
            if row.winfo_ismapped():
                self.assertEqual(row.winfo_y(), self.dialog.results.bbox(row.item, "audio")[1] + 1)
        self.dialog.results_filter.value.set("no existe esta canción")
        self.dialog.filter_results()
        self.root.update()
        self.assertFalse(any(r.winfo_ismapped() for r in self.audio.rows))

    def test_error_survives_worker_exit_and_clear_stops_playback(self):
        job = self.start()
        job.events.put(dict(event="audio", status="error", text="Audio no disponible"))
        job.events.put(dict(event="audio_done"))
        self.audio.poll()
        self.assertIn("no disponible", self.dialog.player_status_var.get())
        self.assertIsNone(self.audio.job)
        job = self.start()
        self.dialog.clear_results()
        self.wait_for(lambda: job.cancel.called)
        self.assertIsNone(self.audio.item)


if __name__ == "__main__":
    unittest.main(verbosity=2)
