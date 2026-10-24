"""Regresión de listas copiadas completas: una fila por canción, no por renglón."""

from pathlib import Path
import unittest

from canciones import MAX_QUERIES, clean_queries
from importar_texto import parse_exported_playlist


FIXTURE = Path(__file__).parent.parent / "fixtures_data" / "lista_copiada.txt"

# Los once bloques de colaboraciones que antes dividían la lista driving.
COLLABORATIONS = [
    ("Sunroof", "Dazy\n&\nNicky Youre", "Dazy & Nicky Youre", "", "2:55"),
    ("Crystal Skies (Sped Up)", "VXLLAIN\n,\niGRES\n&\nENXK", "VXLLAIN, iGRES & ENXK", "Crystal Skies", "2:34"),
    ("Get Lucky", "Daft Punk\n,\nPharrell Williams\n&\nNile Rodgers", "Daft Punk, Pharrell Williams & Nile Rodgers", "2010s Hits", "4:09"),
    ("Get Lucky", "Daft Punk\n,\nPharrell Williams\n&\nNile Rodgers", "Daft Punk, Pharrell Williams & Nile Rodgers", "Get Lucky", "4:09"),
    ("Sunflower", "Post Malone\n&\nSwae Lee", "Post Malone & Swae Lee", "Spider-Man", "2:39"),
    ("Finesse (Remix)", "Bruno Mars\n&\nCardi B", "Bruno Mars & Cardi B", "Finesse (Remix)", "3:38"),
    ("Happier", "Marshmello\n&\nBastille", "Marshmello & Bastille", "Happier", "3:35"),
    ("Under Control (feat. Hurts)", "Calvin Harris\n&\nAlesso", "Calvin Harris & Alesso", "Motion", "3:05"),
    ("Happy Now", "Kygo\n&\nSandro Cavazza", "Kygo & Sandro Cavazza", "Happy Now", "3:32"),
    ("Risin' to the Top (A Mike Maurro Mix)", "Keni Burke\n&\nMike Maurro", "Keni Burke & Mike Maurro", "The Mike Maurro Remix Vault", "8:50"),
    ("Jungle", "Alok\n,\nThe Chainsmokers\n&\nMae Stephens", "Alok, The Chainsmokers & Mae Stephens", "Jungle", "2:56"),
]


class ExportedPlaylistTests(unittest.TestCase):
    def test_collaborations_produce_one_row_with_artists_album_and_duration(self):
        for title, body, artist, album, duration in COLLABORATIONS:
            for separator in ("\n", "\n\n"):
                with self.subTest(title=title, separator=separator):
                    lines = [title, *body.splitlines(), *([album] if album else []), duration]
                    parsed = parse_exported_playlist(separator.join(lines))
                    self.assertEqual(len(parsed.songs), 1)
                    song = parsed.songs[0]
                    self.assertEqual((song.title, song.artist, song.album, song.duration), (title, artist, album, duration))
                    self.assertFalse(song.review_reason)
                    self.assertFalse(parsed.warnings)

    def test_167_records_with_all_eleven_collaborations_do_not_expand(self):
        blocks = [f"Canción {index}\nArtista {index}\nÁlbum {index}\n3:45" for index in range(156)]
        for title, body, _, album, duration in COLLABORATIONS:
            blocks.append("\n".join([title, body, *([album] if album else []), duration]))
        parsed = parse_exported_playlist("\n\n".join(blocks))
        self.assertEqual((len(parsed.songs), parsed.timed_blocks), (167, 167))
        self.assertFalse(parsed.warnings)
        self.assertTrue(all(song.structured for song in parsed.songs))

    def test_separators_attached_to_artist_names_and_non_latin_names(self):
        for body, artist in (("Dazy &\nNicky Youre", "Dazy & Nicky Youre"),
                             ("Dazy\n& Nicky Youre", "Dazy & Nicky Youre"),
                             ("A,\nB\n&\nC", "A, B & C"),
                             ("A\nfeat.\nB", "A feat. B"),
                             ("宇多田ヒカル\n、\n椎名林檎", "宇多田ヒカル, 椎名林檎")):
            with self.subTest(body=body):
                song = parse_exported_playlist(f"Tema\n{body}\nDisco\n3:00").songs[0]
                self.assertEqual(song.artist, artist)
                self.assertEqual(song.album, "Disco")

    def test_ambiguous_blocks_keep_original_once_instead_of_generating_queries(self):
        for body in ("Tema\nArtista\nDisco\nDato desconocido", "Tema\nArtista\n\nDisco\nDato desconocido",
                     "Tema\nArtista\n&", "Tema"):
            with self.subTest(body=body):
                parsed = parse_exported_playlist("Hello\nAdele\n21\n4:55\n\n" + body + "\n3:00")
                self.assertEqual(len(parsed.songs), 2)
                song = parsed.songs[-1]
                self.assertTrue(song.review_reason)
                self.assertEqual(song.duration, "3:00")
                self.assertEqual(song.raw_text, "\n".join(line for line in body.splitlines() if line))
                self.assertTrue(parsed.warnings)

    def test_album_names_starting_with_joiner_words_are_not_artists(self):
        for album in ("And Justice for All", "Y ahora", "Feat. The World"):
            song = parse_exported_playlist(f"Tema\nArtista\n{album}\n3:00").songs[0]
            self.assertEqual(song.artist, "Artista")
            self.assertEqual(song.album, album)

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

    def test_explicit_video_credits_keep_artist_channel_title_and_duration(self):
        cases = [
            ("My Hero Academia Season 6 Opening 1 | Hitamuki by SUPER BEAVER", "Crunchyroll", "SUPER BEAVER"),
            ("My Hero Academia Season 6 Opening 2 | Bokurano by Eve", "Crunchyroll", "Eve"),
            ("My Hero Academia Ending 1 | Heroes by Brian the Sun", "Crunchyroll", "Brian the Sun"),
            ("My Hero Academia Season 5 Opening 1 | No.1 by DISH//", "Crunchyroll", "DISH//"),
            ("Midnight Blues - Ichiro Araki (1981) Ashita no Joe Opening 2", "HeyGen", "Ichiro Araki"),
            ("Dragon Ball Super Opening Full |「Chozetsu Dynamic」By Kazuya Yoshii", "KiriLody", "Kazuya Yoshii"),
            ('Cyberpunk | “I Really Want to Stay At Your House” by Rosa Walton | Music Video', "Netflix", "Rosa Walton"),
        ]
        for title, channel, artist in cases:
            with self.subTest(title=title):
                parsed = parse_exported_playlist(f"{title}\n{channel}\n1:45")
                self.assertEqual(len(parsed.songs), 1)
                song = parsed.songs[0]
                self.assertEqual((song.artist, song.uploader, song.title, song.duration),
                                 (artist, channel, title, "1:45"))
                self.assertEqual(song.query, title)  # Mantener la versión y no repetir el artista.

    def test_ambiguous_or_truncated_titles_preserve_channel_without_inventing_artist(self):
        for title in ("My Hero Academia Season 4 Opening 1 | Polaris",
                      "My Hero Academia Ending | Stand by Me",
                      "My Hero Academia Ending | Shout Baby by Ryokusho..."):
            with self.subTest(title=title):
                song = parse_exported_playlist(f"{title}\nCrunchyroll\n1:40").songs[0]
                self.assertEqual(song.artist, "")
                self.assertEqual(song.uploader, "Crunchyroll")
                self.assertEqual(song.query, title)

    def test_line_endings_bom_and_blank_lines_between_fields(self):
        text = "\ufeffGunjo Sanka\r\n\r\nEve\r\n\r\nKaizin\r\n\r\n4:37"
        parsed = parse_exported_playlist(text)
        self.assertEqual(len(parsed.songs), 1)
        self.assertEqual(parsed.songs[0].query, "Eve - Gunjo Sanka")
        for body in ("Gunjo Sanka\n\nEve\nKaizin", "Gunjo Sanka\nEve\n\nKaizin"):
            parsed = parse_exported_playlist(body + "\n4:37")
            self.assertEqual(len(parsed.songs), 1)
            self.assertEqual(parsed.songs[0].query, "Eve - Gunjo Sanka")
            self.assertEqual(parsed.songs[0].album, "Kaizin")

    def test_regular_queries_and_time_named_song_are_not_misclassified(self):
        for text in ("Eve - Gunjo Sanka\nLONGMAN - spiral", "Jay-Z - 4:44\n4:44",
                     "Adele - Hello\nEve - Gunjo Sanka\n4:44",
                     "spiral\n3:52\nLONGMAN·spiral\nGunjo Sanka\n4:37\nEve·Kaizin"):
            self.assertIsNone(parse_exported_playlist(text))

    def test_missing_last_duration_preserves_record_and_reports_it(self):
        parsed = parse_exported_playlist("Hello\nAdele\n21\n4:55\n\nspiral\nLONGMAN\nspiral")
        self.assertEqual(len(parsed.songs), 2)
        self.assertEqual(parsed.songs[-1].query, "LONGMAN - spiral")
        self.assertTrue(parsed.warnings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
