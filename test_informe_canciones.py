"""Regresiones: 134/129, playlist 137/134/3 y reintentos sin perder elecciones."""

from contextlib import redirect_stdout
import gc
import io
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import canciones
import descargador_gui as backend
from importar_canciones import ImportSongsDialog
from informe_canciones import playlist_url, inspect_playlist, error_reason, selection_transfer, transfer_text


def playlist_fixture():
    entries = [dict(id=f"video{i}", title=f"Canción {i}") for i in range(1, 138)]
    for position in (41, 75, 128):
        entries[position - 1]["title"] = None
    return dict(title="Lista de prueba", playlist_count=137, entries=entries)


class ReportBackendTests(unittest.TestCase):
    def test_playlist_137_includes_three_unavailable_positions_and_links(self):
        result = inspect_playlist(playlist_fixture())
        self.assertEqual((result["total"], result["readable"], len(result["unavailable"])), (137, 134, 3))
        self.assertEqual([item["position"] for item in result["unavailable"]], [41, 75, 128])
        self.assertTrue(all(item["url"] and item["reason"] for item in result["unavailable"]))

    def test_private_deleted_and_incomplete_playlist_are_not_silently_lost(self):
        result = inspect_playlist(dict(playlist_count=5, entries=[None,
            dict(title="[Private video]", id="private"), dict(title="[Deleted video]", id="deleted")]))
        self.assertEqual(result["unaccounted"], 2)
        self.assertEqual(len(result["unavailable"]), 3)
        self.assertIn("privado", result["unavailable"][1]["reason"])
        self.assertIn("eliminado", result["unavailable"][2]["reason"])
        with self.assertRaises(ValueError):
            inspect_playlist(None)

    def test_playlist_url_validation(self):
        self.assertEqual(playlist_url("https://music.youtube.com/playlist?list=PLtest_-&x=1"),
                         "https://www.youtube.com/playlist?list=PLtest_-")
        self.assertEqual(playlist_url(""), "")
        for value in ("https://example.com/?list=test", "https://youtube.com/watch?v=abc", "https://youtube.com.evil.test/?list=abc"):
            with self.assertRaises(ValueError):
                playlist_url(value)

    def test_empty_unavailable_live_and_none_data_have_reasons(self):
        downloader = Mock()
        downloader.extract_info.return_value = dict(entries=[])
        diagnostics = {}
        self.assertEqual(canciones.search_candidates("Nombre", downloader, diagnostics), [])
        self.assertIn("no devolvió resultados", diagnostics["reason"])
        downloader.extract_info.return_value = dict(entries=[dict(id="live", title="Live", is_live=True),
            dict(id="private", title="[Private video]"), dict(id="no_title")])
        self.assertEqual(canciones.search_candidates("Nombre", downloader, diagnostics), [])
        self.assertIn("3 resultados", diagnostics["reason"])
        downloader.extract_info.return_value = None
        with self.assertRaisesRegex(ValueError, "no devolvió datos"):
            canciones.search_candidates("Nombre", downloader)

    def test_worker_reports_empty_and_exception_and_preserves_retry_indices(self):
        downloader = Mock()
        downloader.extract_info.side_effect = [dict(entries=[]), TimeoutError("timed out")]
        output = io.StringIO()
        with patch("yt_dlp.YoutubeDL") as factory, redirect_stdout(output):
            factory.return_value.__enter__.return_value = downloader
            status = canciones.run_import_worker(dict(task="search", queries=["A", "B"], query_indices=[7, 12]))
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        results = [event for event in events if event["event"] == "search_result"]
        self.assertEqual([event["index"] for event in results], [7, 12])
        self.assertEqual([event["progress_index"] for event in results], [1, 2])
        self.assertIn("no devolvió resultados", results[0]["reason"])
        self.assertTrue(results[1]["failed"])
        self.assertIn("tiempo de espera", results[1]["reason"])
        self.assertEqual(status, 1)

    def test_worker_checks_playlist_without_downloading(self):
        downloader = Mock()
        downloader.extract_info.return_value = playlist_fixture()
        output = io.StringIO()
        with patch("yt_dlp.YoutubeDL") as factory, redirect_stdout(output):
            factory.return_value.__enter__.return_value = downloader
            canciones.run_import_worker(dict(task="playlist", playlist_url="https://music.youtube.com/playlist?list=PLtest"))
        event = next(json.loads(line) for line in output.getvalue().splitlines() if json.loads(line)["event"] == "playlist_report")
        self.assertEqual(len(event["report"]["unavailable"]), 3)
        downloader.extract_info.assert_called_once_with("https://www.youtube.com/playlist?list=PLtest", download=False)

    def test_error_messages_explain_rate_limit_and_auth(self):
        self.assertIn("limitó", error_reason("HTTP Error 429"))
        self.assertIn("sesión", error_reason("Sign in to confirm you are not a bot"))

    def test_transfer_identifies_both_names_that_share_a_video(self):
        report = selection_transfer([dict(query="Canción A", title="Versión compartida", url="same"),
                                     dict(query="Canción B", title="Versión compartida", url="same")])
        self.assertEqual((report["selected"], report["unique"], report["repeated"]), (2, 1, 1))
        self.assertEqual(report["urls"], ["same"])
        self.assertIn("Canción A", transfer_text(report))
        self.assertIn("Canción B", transfer_text(report))
        with self.assertRaises(ValueError):
            selection_transfer([dict(query="Sin enlace", title="Sin enlace", url="")])


class ReportDialogTests(unittest.TestCase):
    def setUp(self):
        self.root = backend.launch_gui()
        self.root.withdraw()
        self.dialog = ImportSongsDialog(self.root, lambda urls: False)
        self.dialog.withdraw()

    def tearDown(self):
        self.root.destroy()
        self.root = self.dialog = None
        gc.collect()

    def start(self, count=3):
        self.dialog.names.insert("1.0", "\n".join(f"Artista - Canción {index}" for index in range(count)))
        with patch.object(self.dialog, "start_job"):
            self.dialog.start_search()
        self.dialog.task = "search"
        self.dialog.set_busy(True)

    def result(self, index, *, empty=False, failed=False, reason=""):
        self.dialog.handle_event(dict(event="search_result", index=index, query=self.dialog.searched_queries[index],
            candidates=[] if empty else [dict(title=f"Canción {index}", channel="Artista", duration=240, url=f"url{index}")],
            failed=failed, reason=reason, total=len(self.dialog.searched_queries)))

    def done(self, cancelled=False):
        self.dialog.handle_event(dict(event="job_done", cancelled=cancelled))

    def test_134_searches_129_choices_report_all_five_names_without_success_message(self):
        self.start(134)
        for index in range(134):
            self.result(index, empty=index >= 129, reason="YouTube no devolvió resultados.")
        self.done()
        self.assertEqual(len(self.dialog.selected_candidates), 129)
        self.assertIn("5 pendientes", self.dialog.status_var.get())
        self.assertIn("5 sin resultados", self.dialog.status_var.get())
        self.assertEqual(self.dialog.tabs.select(), str(self.dialog.report_tab))
        text = self.dialog.report_text.get("1.0", "end")
        for index in range(129, 134):
            self.assertIn(f"Artista - Canción {index}", text)
        self.assertEqual(str(self.dialog.retry_button["state"]), "normal")

    def test_retry_only_failed_queries_keeps_good_selection_and_progress(self):
        self.start()
        self.result(0)
        self.result(1, empty=True, failed=True, reason="Timeout de prueba")
        self.result(2, empty=True, reason="Sin coincidencias de prueba")
        self.done()
        chosen = self.dialog.selected_candidates[0]
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.retry_pending()
        config = start.call_args.args[0]
        self.assertEqual(config["query_indices"], [1, 2])
        self.assertEqual(len(config["queries"]), 2)
        self.assertEqual(self.dialog.selected_candidates, {0: chosen})
        self.dialog.set_busy(True)
        self.dialog.handle_event(dict(event="search_result", index=2, query=self.dialog.searched_queries[2], candidates=[
            dict(title="Canción 2", channel="Artista", duration=200, url="retry2")], total=2, progress_index=2))
        self.assertEqual(float(self.dialog.progress["value"]), 100)
        self.result(1)
        self.done()
        self.assertEqual(len(self.dialog.selected_candidates), 3)
        self.assertEqual(self.dialog.selected_candidates[0], chosen)
        self.assertEqual(len(self.dialog.result_groups), 3)
        self.assertIn("0 pendientes", self.dialog.status_var.get())

    def test_report_records_alternative_queries_without_changing_the_original(self):
        self.start(1)
        original = self.dialog.searched_queries[0]
        self.dialog.handle_event(dict(event="search_result", index=0, query=original, total=1,
            candidates=[dict(title="Versión encontrada", channel="Artista", duration=200, url="found")],
            search_attempts=[dict(query=original, limit=3, received=0, skipped=0),
                             dict(query="Artista Canción 0", limit=3, received=3, skipped=0)],
            matched_query="Artista Canción 0"))
        self.done()
        report = self.dialog.report_text.get("1.0", "end")
        self.assertIn(original + " → 0 resultados", report)
        self.assertIn("Artista Canción 0 → 3 resultados", report)
        self.assertEqual(self.dialog.searched_queries, [original])
        self.assertEqual(len(self.dialog.selected_candidates), 1)

    def test_cancelled_and_missing_results_have_names_and_can_retry(self):
        self.start()
        self.result(0)
        self.done(cancelled=True)
        self.assertIn("cancelada", self.dialog.status_var.get())
        self.assertIn("2 sin completar", self.dialog.status_var.get())
        text = self.dialog.report_text.get("1.0", "end")
        self.assertIn("Canción 1", text)
        self.assertIn("Canción 2", text)
        self.assertEqual(self.dialog.pending_indices(retryable=True), [1, 2])

    def test_playlist_unavailable_and_search_pending_are_reported_separately(self):
        self.start()
        self.dialog.handle_event(dict(event="playlist_report", report=inspect_playlist(playlist_fixture())))
        self.result(0)
        self.result(1)
        self.result(2, empty=True, failed=True, reason="HTTP Error 429")
        self.done()
        text = self.dialog.report_text.get("1.0", "end")
        self.assertIn("137 entradas en total", text)
        self.assertIn("3 no disponibles", text)
        self.assertIn("1 pendientes", text)
        self.assertIn("HTTP Error 429", text)
        self.assertIn("Posición 128", text)

    def test_playlist_check_does_not_clear_choices_and_validation_is_explicit(self):
        self.start(1)
        self.result(0)
        self.done()
        chosen = dict(self.dialog.selected_candidates)
        self.dialog.playlist_var.set("https://music.youtube.com/playlist?list=PLtest")
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.check_playlist()
        self.assertEqual(start.call_args.args[0]["task"], "playlist")
        self.assertEqual(self.dialog.selected_candidates, chosen)
        self.dialog.playlist_var.set("https://example.com")
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.check_playlist()
        start.assert_not_called()

    def test_report_saves_utf8_and_manual_unselect_does_not_retry_a_successful_search(self):
        self.start(1)
        self.result(0)
        self.done()
        item = self.dialog.selected_candidates[0]
        self.dialog.results.selection_set(item)
        self.dialog.choose_result()
        self.assertEqual(self.dialog.pending_indices(), [0])
        self.assertEqual(self.dialog.pending_indices(retryable=True), [])
        self.assertIn("ninguna está elegida", self.dialog.report_text.get("1.0", "end"))
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "informe.txt"
            with patch("importar_canciones.filedialog.asksaveasfilename", return_value=str(target)):
                self.dialog.save_report()
            self.assertIn("Canción 0", target.read_text(encoding="utf-8"))

    def test_malformed_worker_result_is_reported_without_stopping_event_loop(self):
        self.start(1)
        self.dialog.job = canciones.ImportJob()
        self.dialog.job.events.put(dict(event="search_result", index=0, query=self.dialog.searched_queries[0],
            candidates=[dict(title="Canción 0", channel="Artista", duration={}, url="url0")], total=1))
        self.dialog.job.events.put(dict(event="job_done", cancelled=False))
        self.dialog.poll_events()
        self.assertFalse(self.dialog.busy)
        self.assertIn("1 errores", self.dialog.status_var.get())
        self.assertIn("TypeError", self.dialog.report_text.get("1.0", "end"))
        self.assertEqual(self.dialog.pending_indices(retryable=True), [0])

    def test_129_choices_to_128_urls_requires_confirmation_and_preserves_names_in_main(self):
        self.start(129)
        for index in range(129):
            url_index = 127 if index == 128 else index
            self.dialog.handle_event(dict(event="search_result", index=index, query=self.dialog.searched_queries[index],
                candidates=[dict(title=f"Video {url_index}", channel="Artista", duration=240,
                                 url=f"https://www.youtube.com/watch?v=video{url_index}")], total=129))
        self.done()
        self.dialog.on_add = Mock(return_value=True)
        with patch("importar_canciones.messagebox.askyesno", return_value=False) as ask:
            self.dialog.add_selected()
        self.dialog.on_add.assert_not_called()
        self.assertEqual(len(self.dialog.selected_candidates), 129)
        self.assertEqual(self.root.urls.get("1.0", "end").strip(), "")
        self.assertIn("129 elecciones", ask.call_args.args[1])
        report = self.dialog.report_text.get("1.0", "end")
        self.assertIn("Artista - Canción 127", report)
        self.assertIn("Artista - Canción 128", report)
        self.dialog.on_add = self.root.add_song_urls
        self.dialog.on_transfer = self.root.record_song_transfer
        with patch("importar_canciones.messagebox.askyesno", return_value=True):
            self.dialog.add_selected()
        self.assertEqual(len(self.root.urls.get("1.0", "end").strip().splitlines()), 128)
        self.assertIn("129 elecciones → 128 videos únicos", self.root.status_var.get())
        self.assertIn("128 nuevos", self.root.status_var.get())
        self.assertEqual(self.root.notebook.select(), str(self.root.import_tab))
        stored = self.root.import_report.get("1.0", "end")
        self.assertIn("Artista - Canción 127", stored)
        self.assertIn("Artista - Canción 128", stored)
        self.assertFalse(self.root.running)

    def test_already_queued_urls_have_explicit_counts_and_are_not_appended_twice(self):
        url = "https://www.youtube.com/watch?v=existing"
        new_url = "https://www.youtube.com/watch?v=new"
        self.root.urls.insert("1.0", url)
        self.assertTrue(self.root.add_song_urls([url, new_url, new_url]))
        self.assertEqual(self.root.urls.get("1.0", "end").strip().splitlines(), [url, new_url])
        self.assertEqual(self.root.last_queue_addition, dict(incoming=3, unique=2, added=1, existing=1, repeated=1))
        self.assertIn("1 ya estaban", self.root.status_var.get())
        self.assertIn("3 enlaces recibidos", self.root.log.get("1.0", "end"))

    def test_rejected_or_failed_queue_handoff_keeps_choices(self):
        self.start(1)
        self.result(0)
        self.done()
        self.dialog.on_add = Mock(return_value=False)
        self.dialog.add_selected()
        self.assertEqual(len(self.dialog.selected_candidates), 1)
        self.assertIn("No se añadieron", self.dialog.status_var.get())
        self.dialog.on_add = Mock(side_effect=OSError("Fallo de prueba"))
        self.dialog.add_selected()
        self.assertTrue(self.dialog.winfo_exists())
        self.assertEqual(len(self.dialog.selected_candidates), 1)
        self.assertIn("Fallo de prueba", self.dialog.report_text.get("1.0", "end"))


if __name__ == "__main__":
    unittest.main()
