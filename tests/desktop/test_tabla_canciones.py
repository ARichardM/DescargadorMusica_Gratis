"""Pruebas de revisión tabular, edición, selección y búsquedas por fila."""

import gc
import time
import unittest
from unittest.mock import patch
from pathlib import Path

import canciones
import descargador_gui as backend
from importar_canciones import ImportSongsDialog
from tabla_canciones import SongEntry
from coincidencias import seconds


class SongEntryTests(unittest.TestCase):
    def test_missing_artist_and_opening_are_not_invented(self):
        for query in ("Gunjo Sanka", "Boruto Opening 7 - Hajimatteiku Takamatteiku"):
            entry = SongEntry.from_query(query)
            self.assertEqual(entry.artist, "")
            self.assertEqual(entry.title, query)
            self.assertEqual(entry.state, "Revisar artista")
        entry = SongEntry.from_query("Mrs. GREEN APPLE - Inferno", "Foto.png")
        self.assertEqual(entry.artist, "Mrs. GREEN APPLE")
        self.assertEqual(entry.title, "Inferno")
        self.assertEqual(entry.source, "Foto.png")


class TableWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.root = backend.launch_gui()
        self.root.withdraw()
        self.received = []
        self.dialog = ImportSongsDialog(self.root, lambda urls: self.received.extend(urls))
        self.dialog.withdraw()

    def tearDown(self):
        if self.dialog.winfo_exists():
            self.dialog.destroy()
        self.root.destroy()
        self.dialog = self.root = None
        gc.collect()

    def populate(self, text="LONGMAN - spiral\nEve - Gunjo Sanka"):
        self.dialog.names.insert("1.0", text)
        self.dialog.sync_table_from_text()
        return self.dialog.songs.entries()

    def candidate_event(self, index=0, candidates=None):
        entry = self.dialog.songs.items[self.dialog.search_row_ids[index]]
        return dict(index=index, query=self.dialog.searched_queries[index], candidates=candidates if candidates is not None else [
            dict(title=entry.title, channel=entry.artist, duration=seconds(entry.duration) or 240,
                 url=f"https://www.youtube.com/watch?v=version{index}")], total=len(self.dialog.searched_queries))

    def test_ambiguous_import_is_one_unchecked_row_with_original_and_reason_in_report(self):
        body = "Tema dudoso\nArtista\nDisco\nDato desconocido"
        rows = self.populate("Hello\nAdele\n21\n4:55\n\n" + body + "\n3:00")
        self.assertEqual(len(rows), 2)
        item, entry = rows[1]
        self.assertFalse(entry.checked)
        self.assertEqual(entry.state, "Revisar bloque")
        report = self.dialog.report_text.get("1.0", "end")
        self.assertIn("1 bloques ambiguos", report)
        self.assertIn(body, report)
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.start_search()
        self.assertEqual(start.call_args.args[0]['queries'], ['Adele - Hello'])
        self.dialog.songs.edit_value(item, "artist", "Artista corregido")
        self.assertFalse(entry.review_reason)
        self.assertEqual(entry.raw_text, body)

    def test_weak_result_is_pending_with_reason_but_can_be_chosen_manually(self):
        self.populate("Kygo - Happy Now")
        with patch.object(self.dialog, "start_job"):
            self.dialog.start_search()
        self.dialog.add_candidates(self.candidate_event(0, [dict(title="Zedd - Happy Now", channel="Zedd",
                                                               duration=210, url="otra-cancion")]))
        self.assertFalse(self.dialog.selected_candidates)
        self.assertEqual(self.dialog.pending_indices(), [0])
        item = next(iter(self.dialog.candidates))
        self.assertEqual(self.dialog.results.set(item, "chosen"), "Revisar · sin marcar")
        self.assertEqual(self.dialog.songs.entries()[0][1].state, "Revisar coincidencia")
        self.dialog.task = "search"
        self.dialog.handle_event(dict(event="job_done", cancelled=False))
        self.assertIn("1 pendientes", self.dialog.status_var.get())
        self.assertIn("artista", self.dialog.report_text.get("1.0", "end"))
        self.assertEqual(self.dialog.tabs.select(), str(self.dialog.report_tab))
        self.dialog.results.selection_set(item)
        self.dialog.choose_result()
        self.dialog.add_selected()
        self.assertEqual(self.received, ["otra-cancion"])

    def test_manually_checked_ambiguous_block_cannot_be_auto_selected(self):
        rows = self.populate("Hello\nAdele\n21\n4:55\n\nTema\nArtista\nDisco\nExtra\n3:00")
        rows[0][1].checked = False
        rows[1][1].checked = True
        with patch.object(self.dialog, "start_job"):
            self.dialog.start_search()
        self.dialog.add_candidates(self.candidate_event())
        self.assertFalse(self.dialog.selected_candidates)
        self.assertIn("separar", self.dialog.report_text.get("1.0", "end"))

    def test_ocr_builds_table_and_keeps_raw_text_separate(self):
        dialog = self.dialog
        dialog.job = canciones.ImportJob()
        dialog.task = "ocr"
        dialog.set_busy(True)
        dialog.handle_event(dict(event="ocr_result", lines=["Eve - Gunjo Sanka", "spiral"],
                                 raw_text="Gunjo Sanka\n4:37\nEve·Kaizin\nspiral", name="Foto.png", index=1, total=1))
        dialog.handle_event(dict(event="job_done", cancelled=False))
        rows = dialog.songs.entries()
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[0][1].artist, rows[0][1].title, rows[0][1].source), ("Eve", "Gunjo Sanka", "Foto.png"))
        self.assertEqual(rows[1][1].state, "Revisar artista")
        self.assertIn("4:37", dialog.raw_text.get("1.0", "end"))
        self.assertNotIn("4:37", dialog.names.get("1.0", "end"))
        self.assertEqual(dialog.tabs.select(), str(dialog.table_tab))

    def test_actual_pasted_export_builds_133_rows_with_metadata(self):
        text = (Path(__file__).parent.parent / "fixtures_data" / "lista_copiada.txt").read_text(encoding="utf-8")
        self.populate(text)
        rows = self.dialog.songs.entries()
        self.assertEqual(len(rows), 133)
        self.assertEqual(rows[0][1].artist, "WANIMA")
        self.assertEqual(rows[0][1].title, "消えない理由 - Kienai Riyuu")
        self.assertEqual(rows[0][1].duration, "4:10")
        self.assertEqual(self.dialog.songs.tree.set(rows[0][0], "duration"), "4:10")
        self.assertIn("133 canciones", self.dialog.songs.count_var.get())
        self.assertIn("WANIMA", self.dialog.raw_text.get("1.0", "end"))
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.start_search()
        self.assertEqual(len(start.call_args.args[0]["queries"]), 133)
        self.assertEqual(len(self.dialog.search_row_ids), 133)

    def test_text_choices_reach_queue_in_source_order(self):
        self.populate("Zeta - Última letra\nAlfa - Primera letra\nMedio - Otra canción")
        self.assert_choices_keep_source_order()

    def test_pasted_video_rows_show_channel_and_recover_credits_without_changing_search(self):
        titles = ["My Hero Academia Season 4 Opening 1 | Polaris",
                  "My Hero Academia Season 6 Opening 1 | Hitamuki by SUPER BEAVER",
                  "My Hero Academia Season 6 Opening 2 | Bokurano by Eve"]
        rows = self.populate("\n".join(f"{title}\nCrunchyroll\n1:40" for title in titles))
        table = self.dialog.songs
        self.assertEqual(table.tree.heading("artist", "text"), "ARTISTA / CANAL")
        self.assertEqual([table.tree.set(item, "artist") for item, _ in rows],
                         ["Crunchyroll (canal)", "SUPER BEAVER", "Eve"])
        self.assertEqual(rows[0][1].state, "Canal disponible")
        self.assertEqual([entry.uploader for _, entry in rows], ["Crunchyroll"] * 3)
        self.assertEqual([entry.duration for _, entry in rows], ["1:40"] * 3)
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.start_search()
        self.assertEqual(start.call_args.args[0]["queries"], titles)
        self.dialog.add_candidates(self.candidate_event(1, [
            dict(title="Hitamuki (full)", channel="SUPER BEAVER", duration=240, url="full"),
            dict(title=titles[1], channel="Crunchyroll", duration=100, url="original")]))
        chosen = self.dialog.selected_candidates[1]
        self.assertEqual(self.dialog.candidates[chosen][1]["url"], "original")

    def test_ocr_keeps_channels_in_table_without_using_them_as_performers(self):
        title = "My Hero Academia Season 4 Opening 1 | Polaris"
        self.dialog.task = "ocr"
        self.dialog.job = canciones.ImportJob()
        self.dialog.set_busy(True)
        self.dialog.handle_event(dict(event="ocr_result", lines=[title],
            uploaders={title.casefold(): "Crunchyroll"}, name="Foto.png", index=1, total=1))
        self.dialog.handle_event(dict(event="job_done", cancelled=False))
        item, entry = self.dialog.songs.entries()[0]
        self.assertEqual(entry.artist, "")
        self.assertEqual(entry.uploader, "Crunchyroll")
        self.assertEqual(self.dialog.songs.tree.set(item, "artist"), "Crunchyroll (canal)")
        self.assertEqual(entry.query, title)
        self.dialog.songs.filter.value.set("Crunchyroll")
        self.root.update()
        self.assertEqual(self.dialog.songs.tree.get_children(), (item,))

    def test_multiple_images_keep_image_and_row_order_in_queue(self):
        self.dialog.job = canciones.ImportJob()
        self.dialog.task = "ocr"
        self.dialog.set_busy(True)
        for index, lines in enumerate((
                ["Zeta - Última letra", "Alfa - Primera letra"],
                ["Medio - Otra canción"]), 1):
            self.dialog.handle_event(dict(event="ocr_result", lines=lines,
                name=f"Foto{index}.png", index=index, total=2))
        self.dialog.handle_event(dict(event="job_done", cancelled=False))
        self.assertEqual([entry.source for _, entry in self.dialog.songs.entries()],
                         ["Foto1.png", "Foto1.png", "Foto2.png"])
        self.assert_choices_keep_source_order()

    def assert_choices_keep_source_order(self):
        self.dialog.on_add = self.root.add_song_urls
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.start_search()
        self.assertEqual(start.call_args.args[0]["queries"],
                         ["Zeta - Última letra", "Alfa - Primera letra", "Medio - Otra canción"])
        # Recibir y elegir resultados en otro orden no cambia el de la lista.
        for index in (2, 0, 1):
            self.dialog.add_candidates(self.candidate_event(index))
        self.dialog.add_selected()
        self.assertEqual(self.root.urls.get("1.0", "end").strip().splitlines(),
                         [f"https://www.youtube.com/watch?v=version{index}" for index in range(3)])

    def test_duplicate_export_rows_remain_independent_but_search_once(self):
        text = "Hello\nAdele\n21\n4:55\nHello\nAdele\n21\n4:55\nspiral\nLONGMAN\nspiral\n3:52"
        rows = self.populate(text)
        self.assertEqual(len(rows), 3)
        self.assertIsNot(rows[0][1], rows[1][1])
        rows[0][1].checked = False
        self.assertTrue(rows[1][1].checked)
        rows[0][1].checked = True
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.start_search()
        self.assertEqual(start.call_args.args[0]["queries"], ["Adele - Hello", "LONGMAN - spiral"])
        self.dialog.add_candidates(self.candidate_event(0))
        self.assertEqual(len(self.dialog.selected_candidates), 1)
        self.assertEqual(rows[0][1].state, "Elegida")
        self.assertEqual(rows[1][1].state, "Elegida")
        self.assertIn("3 filas marcadas → 2 consultas únicas; 1 repeticiones agrupadas",
                      self.dialog.report_text.get("1.0", "end"))

    def test_cleanup_of_export_preserves_fields_and_duration(self):
        self.populate("Gunjo Sanka\nEve\nKaizin\n4:37\nOver\nLittle Glee Monster\nJuice\n3:58")
        self.dialog.clean_playlist_text()
        self.assertEqual(len(self.dialog.songs.entries()), 2)
        self.assertEqual(self.dialog.songs.entries()[0][1].duration, "4:37")
        self.assertEqual(self.dialog.songs.entries()[0][1].album, "Kaizin")

    def test_cell_edits_update_queries_and_keep_original_reference(self):
        rows = self.populate()
        table = self.dialog.songs
        table.edit_value(rows[0][0], "artist", "LONGMAN corregido")
        table.edit_value(rows[0][0], "title", "spiral versión completa")
        self.assertIn("LONGMAN corregido - spiral versión completa", self.dialog.names.get("1.0", "end"))
        self.assertEqual(table.queries()[0], "LONGMAN corregido - spiral versión completa")
        with self.assertRaises(ValueError):
            table.edit_value(rows[1][0], "title", "")

    def test_pasted_text_updates_table_automatically(self):
        self.dialog.names.insert("1.0", "Eve - Gunjo Sanka\nLONGMAN - spiral")
        deadline = time.monotonic() + 2
        while len(self.dialog.songs.entries()) != 2 and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertEqual(self.dialog.songs.queries(), ["Eve - Gunjo Sanka", "LONGMAN - spiral"])

    def test_inline_editor_commits_cell(self):
        rows = self.populate()
        self.root.deiconify()
        self.dialog.deiconify()
        self.dialog.tabs.select(self.dialog.table_tab)
        self.root.update()
        table = self.dialog.songs
        table.begin_edit(rows[0][0], "title")
        self.assertIsNotNone(table.editor)
        editor = table.editor[0]
        editor.delete(0, "end")
        editor.insert(0, "spiral (full)")
        table.commit_editor()
        self.assertEqual(table.items[rows[0][0]].title, "spiral (full)")
        self.assertIsNone(table.editor)

    def test_only_checked_rows_are_searched_and_selected_urls_are_added(self):
        rows = self.populate()
        self.dialog.songs.items[rows[0][0]].checked = False
        self.dialog.songs.changed()
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.start_search()
        self.assertEqual(start.call_args.args[0]["queries"], ["Eve - Gunjo Sanka"])
        self.assertEqual(self.dialog.search_row_ids, [rows[1][0]])
        self.dialog.add_candidates(self.candidate_event())
        self.assertEqual(len(self.dialog.selected_candidates), 1)
        self.assertEqual(self.dialog.songs.items[rows[1][0]].state, "Elegida")
        self.dialog.add_selected()
        self.assertEqual(self.received, ["https://www.youtube.com/watch?v=version0"])

    def test_search_states_follow_the_correct_row(self):
        rows = self.populate()
        with patch.object(self.dialog, "start_job"):
            self.dialog.start_search()
        self.dialog.handle_event(dict(event="import_status", text="Buscando…", query_index=1))
        self.assertEqual(self.dialog.songs.items[rows[1][0]].state, "Buscando…")
        self.dialog.add_candidates(self.candidate_event(0))
        self.dialog.add_candidates(self.candidate_event(1, []))
        self.assertEqual(self.dialog.songs.items[rows[0][0]].state, "Elegida")
        self.assertEqual(self.dialog.songs.items[rows[1][0]].state, "Sin resultados")
        self.dialog.task = "search"
        self.dialog.handle_event(dict(event="job_done", cancelled=False))
        self.assertEqual(self.dialog.songs.items[rows[1][0]].state, "Sin resultados")

    def test_table_change_invalidates_previous_choices(self):
        rows = self.populate()
        with patch.object(self.dialog, "start_job"):
            self.dialog.start_search()
        self.dialog.add_candidates(self.candidate_event())
        self.assertEqual(len(self.dialog.selected_candidates), 1)
        self.dialog.songs.edit_value(rows[0][0], "title", "otra canción")
        self.assertFalse(self.dialog.selected_candidates)
        self.assertFalse(self.dialog.candidates)
        self.assertEqual(str(self.dialog.add_button["state"]), "disabled")

    def test_sort_remove_and_preserve_unchecked_rows_when_appending(self):
        rows = self.populate()
        table = self.dialog.songs
        table.items[rows[0][0]].checked = False
        table.changed()
        table.sort_by("artist")
        self.assertEqual(table.entries()[0][1].artist, "Eve")
        self.dialog.names.insert("end", "\nWANIMA - Kienai Riyuu")
        self.dialog.sync_table_from_text()
        self.assertFalse(next(entry.checked for _, entry in table.entries() if entry.artist == "LONGMAN"))
        last = table.entries()[-1][0]
        table.tree.selection_set(last)
        table.remove_selected()
        self.assertNotIn("WANIMA", self.dialog.names.get("1.0", "end"))
        self.assertEqual(len(table.entries()), 2)

    def test_best_result_is_marked_while_busy_without_hiding_alternatives(self):
        self.populate("spiral\nLONGMAN\nspiral\n3:52")
        with patch.object(self.dialog, "start_job"):
            self.dialog.start_search()
        self.dialog.set_busy(True)
        options = [
            dict(title="Spiral piano cover", channel="Otro", duration=232, url="cover"),
            dict(title="LONGMAN - spiral", channel="LONGMAN", duration=232, url="exacta"),
            dict(title="LONGMAN - spiral (live)", channel="LONGMAN", duration=250, url="live"),
        ]
        self.dialog.add_candidates(self.candidate_event(candidates=options))
        first, second, third = list(self.dialog.candidates)
        self.assertEqual(self.dialog.selected_candidates, {0: second})
        self.assertEqual(self.dialog.results.set(second, "chosen"), "✓ Auto · exacta")
        self.assertEqual(len(self.dialog.results.get_children(self.dialog.results.parent(second))), 3)
        self.assertEqual(str(self.dialog.add_button["state"]), "disabled")
        self.dialog.task = "search"
        self.dialog.handle_event(dict(event="job_done", cancelled=False))
        self.assertEqual(str(self.dialog.add_button["state"]), "normal")
        self.assertFalse(self.received)  # Marcar no equivale a descargar.
        self.dialog.results.selection_set(third)
        self.dialog.choose_result()
        self.assertEqual(self.dialog.selected_candidates, {0: third})
        self.assertEqual(self.dialog.results.set(second, "chosen"), "")
        self.dialog.choose_result()
        self.assertFalse(self.dialog.selected_candidates)
        self.assertEqual(str(self.dialog.add_button["state"]), "disabled")

    def test_duration_metadata_breaks_ties_and_empty_results_select_nothing(self):
        self.populate("Hello\nAdele\n21\n4:55\nspiral\nLONGMAN\nspiral\n3:52")
        with patch.object(self.dialog, "start_job"):
            self.dialog.start_search()
        options = [dict(title="Hello", channel="Adele", duration=400, url="larga"),
                   dict(title="Hello", channel="Adele", duration=295, url="correcta")]
        self.dialog.add_candidates(self.candidate_event(candidates=options))
        self.dialog.add_candidates(self.candidate_event(1, []))
        chosen = self.dialog.selected_candidates[0]
        self.assertEqual(self.dialog.candidates[chosen][1]["url"], "correcta")
        self.assertNotIn(1, self.dialog.selected_candidates)

    def test_empty_or_unchecked_table_does_not_start_network_job(self):
        self.populate()
        self.dialog.songs.check_all(False)
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.start_search()
        start.assert_not_called()
        self.assertIn("Marca al menos", self.dialog.status_var.get())
        self.dialog.songs.add_empty()
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.start_search()
        start.assert_not_called()
        self.assertIn("Completa el título", self.dialog.status_var.get())

    def test_table_filter_preserves_hidden_rows_checks_and_search_scope(self):
        rows = self.populate()
        table = self.dialog.songs
        table.filter.value.set("EVE sanka")
        self.assertEqual(table.tree.get_children(), (rows[1][0],))
        self.assertEqual(len(table.entries()), 2)
        self.assertEqual(len(table.checked_ids()), 2)
        self.assertIn("1 visibles", table.count_var.get())
        with patch.object(self.dialog, "start_job") as start:
            self.dialog.start_search()
        self.assertEqual(start.call_args.args[0]["queries"], ["LONGMAN - spiral", "Eve - Gunjo Sanka"])
        table.filter.clear()
        self.assertEqual(table.tree.get_children(), tuple(item for item, _ in rows))

    def test_filter_accepts_accents_japanese_and_clears_without_invalidating_choices(self):
        self.populate("Artista - Canción\nWANIMA - 消えない理由")
        table = self.dialog.songs
        with patch.object(self.dialog, "start_job"):
            self.dialog.start_search()
        self.dialog.add_candidates(self.candidate_event())
        choice = dict(self.dialog.selected_candidates)
        table.filter.value.set("CANCION")
        self.assertEqual(len(table.tree.get_children()), 1)
        table.filter.value.set("消えない")
        self.assertEqual(len(table.tree.get_children()), 1)
        table.filter.value.set("inexistente")
        self.assertEqual(table.tree.get_children(), ())
        table.filter.clear()
        self.assertEqual(len(table.tree.get_children()), 2)
        self.assertEqual(self.dialog.selected_candidates, choice)

    def test_sort_edit_and_remove_do_not_drop_filtered_rows(self):
        rows = self.populate("Zeta - Uno\nBeta - Dos\nAlfa - Tres")
        table = self.dialog.songs
        table.filter.value.set("zeta")
        table.sort_by("artist")
        self.assertEqual([entry.artist for _, entry in table.entries()], ["Alfa", "Beta", "Zeta"])
        table.edit_value(rows[0][0], "artist", "Omega")
        self.assertEqual(table.tree.get_children(), ())
        self.assertEqual(len(table.entries()), 3)
        table.filter.value.set("beta")
        table.tree.selection_set(rows[1][0])
        table.remove_selected()
        table.filter.clear()
        self.assertEqual([entry.artist for _, entry in table.entries()], ["Alfa", "Omega"])
        self.assertIn("Omega - Uno", self.dialog.names.get("1.0", "end"))

    def test_replacing_table_deletes_detached_rows_and_reapplies_filter(self):
        old_rows = self.populate()
        table = self.dialog.songs
        table.filter.value.set("Eve")
        table.set_queries(["Eve - Otra", "Adele - Hello"])
        self.assertTrue(all(not table.tree.exists(item) for item, _ in old_rows))
        self.assertEqual(len(table.entries()), 2)
        self.assertEqual(len(table.tree.get_children()), 1)
        table.filter.clear()
        self.assertEqual(len(table.tree.get_children()), 2)

    def test_results_filter_keeps_alternatives_and_hidden_automatic_choices(self):
        self.populate()
        with patch.object(self.dialog, "start_job"):
            self.dialog.start_search()
        self.dialog.results_filter.value.set("Eve")
        self.dialog.add_candidates(self.candidate_event(0, [dict(
            title="spiral", channel="LONGMAN", duration=232, url="spiral")]))
        self.dialog.add_candidates(self.candidate_event(1, [
            dict(title="Gunjo Sanka", channel="Eve", duration=277, url="gunjo"),
            dict(title="Gunjo Sanka (live)", channel="Otro", duration=300, url="live")]))
        self.assertEqual(len(self.dialog.results.get_children()), 1)
        parent = self.dialog.results.get_children()[0]
        self.assertEqual(len(self.dialog.results.get_children(parent)), 2)
        self.assertEqual(len(self.dialog.selected_candidates), 2)
        self.dialog.results_filter.value.set("otro")
        self.assertEqual(self.dialog.results.get_children(), (parent,))
        self.assertEqual(len(self.dialog.results.get_children(parent)), 2)
        self.dialog.add_selected()
        self.assertEqual(self.received, ["spiral", "gunjo"])

    def test_clear_results_removes_hidden_groups(self):
        self.populate()
        with patch.object(self.dialog, "start_job"):
            self.dialog.start_search()
        self.dialog.add_candidates(self.candidate_event())
        old_items = list(self.dialog.candidates) + list(self.dialog.result_groups)
        self.dialog.results_filter.value.set("inexistente")
        self.assertEqual(self.dialog.results.get_children(), ())
        self.dialog.clear_results()
        self.dialog.results_filter.clear()
        self.assertEqual(self.dialog.results.get_children(), ())
        self.assertTrue(all(not self.dialog.results.exists(item) for item in old_items))
        self.assertFalse(self.dialog.selected_candidates)

    def test_table_actions_remain_visible_in_small_window(self):
        self.root.deiconify()
        self.dialog.deiconify()
        self.dialog.geometry("900x650")
        self.dialog.tabs.select(self.dialog.table_tab)
        self.root.update()
        self.assertTrue(self.dialog.table_search_button.winfo_ismapped())
        self.assertTrue(self.dialog.add_button.winfo_ismapped())
        bottom = self.dialog.table_search_button.winfo_rooty() + self.dialog.table_search_button.winfo_height()
        self.assertLess(bottom, self.dialog.winfo_rooty() + self.dialog.winfo_height())


if __name__ == "__main__":
    unittest.main(verbosity=2)
