"""Escucha de coincidencias independiente de las elecciones y las búsquedas."""

import gc
import queue
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import descargador_gui as app
from importar_canciones import ImportSongsDialog


def fake_player():
    cancelled = threading.Event()
    return SimpleNamespace(events=queue.Queue(), cancelled=cancelled, run=Mock(),
                           cancel=Mock(side_effect=cancelled.set))


class ResultPlaybackTests(unittest.TestCase):
    def setUp(self):
        self.root = app.launch_gui()
        self.root.withdraw()
        self.received = []
        self.dialog = ImportSongsDialog(self.root, lambda urls: self.received.extend(urls))
        self.dialog.withdraw()
        self.dialog.add_candidates(dict(index=0, query="Artista - Canción", candidates=[
            dict(title="Versión oficial", channel="Artista", duration=180,
                 url="https://www.youtube.com/watch?v=abcdefghijk"),
            dict(title="Otra versión", channel="Artista", duration=170,
                 url="https://www.youtube.com/watch?v=lmnopqrstuv")]))
        self.rows = list(self.dialog.candidates)

    def tearDown(self):
        self.root.destroy()
        self.dialog = self.root = None
        gc.collect()

    def wait_for(self, condition):
        deadline = time.monotonic() + 5
        while not condition():
            self.assertLess(time.monotonic(), deadline)
            self.root.update()
            time.sleep(0.01)

    def test_preview_during_search_keeps_choices_and_does_not_add_or_download(self):
        self.dialog.set_busy(True)
        self.dialog.results.selection_set(self.rows[1])
        self.root.update()
        self.assertEqual(str(self.dialog.play_button["state"]), "normal")
        choices = dict(self.dialog.selected_candidates)
        job = fake_player()
        with patch("importar_canciones.PlayerJob", return_value=job), patch("importar_canciones.webbrowser.open") as browser:
            self.dialog.preview_result()
            self.wait_for(lambda: job.run.called)
            browser.assert_not_called()
        self.assertEqual(job.run.call_args.args[0]["url"], "https://www.youtube.com/watch?v=lmnopqrstuv")
        self.assertEqual(self.dialog.selected_candidates, choices)
        self.assertFalse(self.received)
        self.assertFalse(self.root.running)
        self.dialog.set_busy(False)

    def test_changing_result_stops_previous_player_and_closing_cancels_current(self):
        first, second = fake_player(), fake_player()
        with patch("importar_canciones.PlayerJob", side_effect=[first, second]):
            self.dialog.results.selection_set(self.rows[0])
            self.dialog.preview_result()
            self.wait_for(lambda: first.run.called)
            self.dialog.results.selection_set(self.rows[1])
            self.dialog.preview_result()
            self.wait_for(lambda: second.run.called)
        first.cancel.assert_called_once()
        self.dialog.close()
        self.wait_for(lambda: second.cancel.called)
        self.assertTrue(second.cancelled.is_set())

    def test_parent_rows_are_not_playable_and_errors_survive_player_exit(self):
        parent = self.dialog.results.parent(self.rows[0])
        self.dialog.results.selection_set(parent)
        self.root.update()
        self.assertEqual(str(self.dialog.play_button["state"]), "disabled")
        with patch("importar_canciones.PlayerJob") as factory:
            self.dialog.preview_result()
            factory.assert_not_called()
        job = fake_player()
        self.dialog.player_job = job
        job.events.put(dict(event="player", status="error", text="El propietario no permite reproducir este video."))
        job.events.put(dict(event="player_done", cancelled=False))
        self.wait_for(lambda: self.dialog.player_job is None)
        self.assertIn("propietario", self.dialog.player_status_var.get())

    def test_clearing_results_stops_playback(self):
        job = fake_player()
        self.dialog.player_job = job
        self.dialog.clear_results()
        self.wait_for(lambda: job.cancel.called)
        self.assertIsNone(self.dialog.player_job)
        self.assertTrue(job.cancelled.is_set())

    def test_playback_actions_fit_in_compact_results_window(self):
        self.root.deiconify()
        self.dialog.deiconify()
        self.dialog.geometry("900x650")
        self.dialog.tabs.select(self.dialog.search_tab)
        self.root.update()
        for button in (self.dialog.play_button, self.dialog.stop_player_button,
                       self.dialog.choose_button, self.dialog.add_button):
            self.assertTrue(button.winfo_ismapped(), button["text"])
            self.assertLess(button.winfo_rooty() + button.winfo_height(),
                            self.dialog.winfo_rooty() + self.dialog.winfo_height())


if __name__ == "__main__":
    unittest.main(verbosity=2)
