"""Regresión de listas copiadas completas: una fila por canción, no por renglón."""

from pathlib import Path
import unittest

from canciones import MAX_QUERIES, clean_queries
from importar_texto import parse_exported_playlist


FIXTURE = Path(__file__).parent / "tests" / "fixtures" / "lista_copiada.txt"


class ExportedPlaylistTests(unittest.TestCase):
    def test_actual_user_file_has_133_records_not_328(self):
        parsed = parse_exported_playlist(FIXTURE.read_text(encoding="utf-8"))
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.timed_blocks, 133)
        self.assertEqual(len(parsed.songs), 133)
        self.assertFalse(parsed.warnings)
        first = parsed.songs[0]
        self.assertEqual((first.artist, first.title, first.album, first.duration),
                         ("WANIMA", "消えない理由 - Kienai Riyuu", "Kienai Riyuu", "4:10"))
        gunjo = next(song for song in parsed.songs if song.title == "Gunjo Sanka")
        self.assertEqual((gunjo.artist, gunjo.album, gunjo.duration), ("Eve", "Kaizin", "4:37"))
        self.assertNotIn("4:10", [song.query for song in parsed.songs])
        self.assertNotIn("Kaizin", [song.query for song in parsed.songs])

    def test_separate_cyberpunk_title_is_preserved_without_merging_first_record(self):
        title = 'Cyberpunk: Edgerunners | “I Really Want to Stay At Your House” by Rosa Walton | Music Video'
        text = "# " + title + "\n\n" + FIXTURE.read_text(encoding="utf-8")
        parsed = parse_exported_playlist(text)
        self.assertEqual(len(parsed.songs), 134)
        self.assertEqual(parsed.songs[0].title, title)
        self.assertEqual(parsed.songs[1].artist, "WANIMA")

    def test_137_records_are_supported_without_truncating_or_adding_rows(self):
        text = "\n\n".join(f"Canción {index}\nArtista {index}\nÁlbum {index}\n\n3:45" for index in range(137))
        parsed = parse_exported_playlist(text)
        self.assertEqual(len(parsed.songs), 137)
        self.assertEqual(len(clean_queries("\n".join(song.query for song in parsed.songs))), 137)
        self.assertGreaterEqual(MAX_QUERIES, 137)

    def test_repeated_tracks_are_not_silently_removed(self):
        parsed = parse_exported_playlist("Hello\nAdele\n21\n4:55\nHello\nAdele\n21\n4:55")
        self.assertEqual(len(parsed.songs), 2)
        self.assertEqual(parsed.songs[0].query, parsed.songs[1].query)
        self.assertIsNot(parsed.songs[0], parsed.songs[1])

    def test_song_aliases_and_album_names_do_not_become_extra_songs(self):
        parsed = parse_exported_playlist("ヒカリアレ - Hikariare\nBURNOUT SYNDROMES\nLemon\n\n4:05")
        self.assertEqual(len(parsed.songs), 1)
        self.assertEqual(parsed.songs[0].artist, "BURNOUT SYNDROMES")
        self.assertEqual(parsed.songs[0].title, "ヒカリアレ - Hikariare")
        self.assertEqual(parsed.songs[0].album, "Lemon")

    def test_video_channel_is_not_assumed_to_be_artist(self):
        parsed = parse_exported_playlist("Boruto Opening 7\nvizmedia\n1:30\nOver\nLittle Glee Monster\nJuice\n3:58")
        self.assertEqual(parsed.songs[0].artist, "")
        self.assertEqual(parsed.songs[0].uploader, "vizmedia")
        self.assertEqual(parsed.songs[1].artist, "Little Glee Monster")

    def test_line_endings_bom_and_blank_lines_between_fields(self):
        text = "\ufeffGunjo Sanka\r\n\r\nEve\r\n\r\nKaizin\r\n\r\n4:37"
        parsed = parse_exported_playlist(text)
        self.assertEqual(len(parsed.songs), 1)
        self.assertEqual(parsed.songs[0].query, "Eve - Gunjo Sanka")

    def test_regular_queries_and_time_named_song_are_not_misclassified(self):
        for text in ("Eve - Gunjo Sanka\nLONGMAN - spiral", "Jay-Z - 4:44\n4:44",
                     "Adele - Hello\nEve - Gunjo Sanka\n4:44"):
            self.assertIsNone(parse_exported_playlist(text))

    def test_missing_last_duration_preserves_record_and_reports_it(self):
        parsed = parse_exported_playlist("Hello\nAdele\n21\n4:55\n\nspiral\nLONGMAN\nspiral")
        self.assertEqual(len(parsed.songs), 2)
        self.assertEqual(parsed.songs[-1].query, "LONGMAN - spiral")
        self.assertTrue(parsed.warnings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
