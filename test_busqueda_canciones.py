"""Búsquedas alternativas acotadas y diagnóstico de resultados vacíos."""

from contextlib import redirect_stdout
import io
import json
import unittest
from unittest.mock import Mock, call, patch

import canciones


def result(identifier="abcdefghijk"):
    return dict(id=identifier, title="SPYAIR - Sakuramitsutsuki", channel="SPYAIR", duration=217)


class SearchFallbackTests(unittest.TestCase):
    def test_multilingual_variants_keep_artist_and_both_titles(self):
        cases = [
            ("SPYAIR - サクラミツツキ - Sakuramitsutsuki", "SPYAIR Sakuramitsutsuki", "SPYAIR サクラミツツキ"),
            ("Eve - 心海 - Shinkai", "Eve Shinkai", "Eve 心海"),
            ("minami - カワキヲアメク -kawakiwomeku", "minami kawakiwomeku", "minami カワキヲアメク"),
        ]
        for original, romanized, native in cases:
            with self.subTest(query=original):
                self.assertEqual(canciones.search_query_variants(original), [original, romanized, native])

    def test_first_success_makes_only_one_request(self):
        downloader = Mock()
        downloader.extract_info.return_value = dict(entries=[result()])
        query = "SPYAIR - サクラミツツキ - Sakuramitsutsuki"
        diagnostics = {}
        self.assertEqual(len(canciones.search_candidates(query, downloader, diagnostics)), 1)
        downloader.extract_info.assert_called_once_with("ytsearch3:" + query, download=False)
        self.assertEqual(diagnostics["matched_query"], query)

    def test_empty_original_recovers_with_romanized_title_and_records_attempts(self):
        downloader = Mock()
        downloader.extract_info.side_effect = [dict(entries=[]), dict(entries=[result()])]
        query = "SPYAIR - サクラミツツキ - Sakuramitsutsuki"
        diagnostics = {}
        candidates = canciones.search_candidates(query, downloader, diagnostics)
        self.assertEqual(candidates[0]["title"], "SPYAIR - Sakuramitsutsuki")
        self.assertEqual(downloader.extract_info.call_args_list, [
            call("ytsearch3:" + query, download=False),
            call("ytsearch3:SPYAIR Sakuramitsutsuki", download=False)])
        self.assertEqual(diagnostics["matched_query"], "SPYAIR Sakuramitsutsuki")
        self.assertEqual([attempt["received"] for attempt in diagnostics["search_attempts"]], [0, 1])

    def test_filtered_top_results_trigger_one_wider_search_and_keep_limit(self):
        downloader = Mock()
        downloader.extract_info.side_effect = [dict(entries=[dict(id="live", title="Live", is_live=True)]),
                                              dict(entries=[result(str(index)) for index in range(6)])]
        candidates = canciones.search_candidates("Nombre", downloader)
        self.assertEqual(len(candidates), 3)
        self.assertEqual(downloader.extract_info.call_args_list,
                         [call("ytsearch3:Nombre", download=False), call("ytsearch10:Nombre", download=False)])

    def test_empty_search_stops_after_bounded_attempts_without_claiming_song_is_missing(self):
        downloader = Mock()
        downloader.extract_info.return_value = dict(entries=[])
        diagnostics = {}
        self.assertEqual(canciones.search_candidates("Eve - 心海 - Shinkai", downloader, diagnostics), [])
        self.assertEqual(downloader.extract_info.call_count, 3)
        self.assertIn("3 consultas", diagnostics["reason"])
        self.assertIn("no confirma", diagnostics["reason"])
        self.assertEqual(diagnostics["matched_query"], "")

    def test_unicode_cleanup_preserves_korean_and_removes_emoji(self):
        original = "서로를 저주해야만 하는 최고의 단짝 💔ㅣ주술회전 2기 ED 등불 (Akari) 가사 번역"
        variants = canciones.search_query_variants(original)
        self.assertEqual(variants[0], original)
        self.assertLessEqual(len(variants), 3)
        self.assertTrue(any("Akari" in variant and "주술회전" in variant and "💔" not in variant
                            for variant in variants[1:]))

    def test_network_failure_does_not_trigger_more_queries(self):
        downloader = Mock()
        downloader.extract_info.side_effect = TimeoutError("timed out")
        with self.assertRaises(TimeoutError):
            canciones.search_candidates("Eve - 心海 - Shinkai", downloader)
        self.assertEqual(downloader.extract_info.call_count, 1)

    def test_worker_preserves_original_query_and_retry_index_after_recovery(self):
        downloader = Mock()
        downloader.extract_info.side_effect = [dict(entries=[]), dict(entries=[result()])]
        original = "SPYAIR - サクラミツツキ - Sakuramitsutsuki"
        output = io.StringIO()
        with patch("yt_dlp.YoutubeDL") as factory, redirect_stdout(output):
            factory.return_value.__enter__.return_value = downloader
            status = canciones.run_import_worker(dict(task="search", queries=[original], query_indices=[50]))
        event = next(json.loads(line) for line in output.getvalue().splitlines()
                     if json.loads(line)["event"] == "search_result")
        self.assertEqual(status, 0)
        self.assertEqual((event["query"], event["index"], event["progress_index"]), (original, 50, 1))
        self.assertEqual(event["matched_query"], "SPYAIR Sakuramitsutsuki")
        self.assertEqual(len(event["search_attempts"]), 2)

    def test_logged_backend_error_is_reported_as_failure_not_empty_search(self):
        downloader = Mock()
        output = io.StringIO()
        with patch("yt_dlp.YoutubeDL") as factory, redirect_stdout(output):
            factory.return_value.__enter__.return_value = downloader

            def backend_error(*args, **kwargs):
                factory.call_args.args[0]["logger"].error("HTTP Error 429")
                return dict(entries=[])

            downloader.extract_info.side_effect = backend_error
            status = canciones.run_import_worker(dict(task="search", queries=["Nombre"]))
        event = next(json.loads(line) for line in output.getvalue().splitlines()
                     if json.loads(line)["event"] == "search_result")
        self.assertEqual(status, 1)
        self.assertTrue(event["failed"])
        self.assertIn("limitó", event["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
