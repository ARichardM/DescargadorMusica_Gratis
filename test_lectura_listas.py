"""Regresiones para capturas con portadas, tiempos y artista/álbum debajo del título."""

from types import SimpleNamespace
import unittest

from canciones import clean_queries, text_from_ocr
from lectura_listas import organize_playlist_text, playlist_crop_bounds


def ocr_result(items):
    return SimpleNamespace(txts=tuple(text for text, x, y, width, height in items), boxes=tuple(
        ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
        for text, x, y, width, height in items))


class PlaylistReadingTests(unittest.TestCase):
    def test_user_pasted_output_is_grouped_and_times_removed(self):
        text = """消えない理由- Kienai Riyuu
4:10
WANIMA· Kienai Riyuu
spiral
3:52
LONGMAN·spiral
Lonely Go!
3:59
Brian the Sun • Lonely Go!(Another Edition)
Boruto Opening 3 (Creditless) (HD) -
Obito Uchiha - 千
Boruto: Naruto Next Generations | Opening 7 - Hajimatteiku Takamatteiku | VIZ
と -
vizmedia
Boruto - Opening 11 | Boruto New Opening -
RANDOM
TVアニメ「ブラッククローバー」1st Season振り返りPV|落書きペイジ/感覚ピ.
1:35
テレ東アニメ
インフェルノ- Inferno
4 -
Mrs. GREEN APPLE · Inferno
Gunjo Sanka
4:37
Eve·Kaizin
ヒカリアレ-Hikariare
上 -
BURNOUT SYNDROMES · Lemon
Over
3:58
Little Glee Monster • Juice"""
        lines = organize_playlist_text(text)
        # El texto plano no permite asegurar que «Obito Uchiha - 千» sea un canal.
        # Se conserva para revisión; la lectura con coordenadas sí distingue el subtítulo.
        self.assertEqual(len(lines), 12, lines)
        self.assertIn("Obito Uchiha - 千", lines)
        self.assertIn("LONGMAN - spiral", lines)
        self.assertIn("Brian the Sun - Lonely Go!", lines)
        self.assertIn("Eve - Gunjo Sanka", lines)
        self.assertIn("Little Glee Monster - Over", lines)
        self.assertFalse(any(line in lines for line in ("4:10", "3:52", "RANDOM", "vizmedia", "と", "上")))
        self.assertFalse(any("Kaizin" in line or "Juice" in line for line in lines))

    def test_layout_excludes_art_and_joins_title_subtitle(self):
        items = []
        pairs = [("spiral", "LONGMAN · spiral", "3:52"),
                 ("Gunjo Sanka", "Eve · Kaizin", "4:37"),
                 ("Boruto Opening 3 (HD)", "Obito Uchiha", "1:32"),
                 ("Over", "Little Glee Monster · Juice", "3:58")]
        for index, (title, subtitle, duration) in enumerate(pairs):
            y = 15 + index * 70
            items.extend([(title, 68, y, 290, 14), (subtitle, 68, y + 25, 310, 14),
                          (duration, 782, y + 9, 30, 13), ("NFORN", 10, y, 35, 10), ("上", 655, y + 10, 10, 14)])
        result = ocr_result(items)
        self.assertEqual(text_from_ocr(result, (832, 300)), [
            "LONGMAN - spiral", "Eve - Gunjo Sanka", "Boruto Opening 3 (HD)", "Little Glee Monster - Over"])
        crop = playlist_crop_bounds(result, (832, 300))
        self.assertIsNotNone(crop)
        self.assertGreater(crop[0], 45)
        self.assertLess(crop[2], 782)

    def test_cropped_list_still_pairs_without_time_column(self):
        items = []
        for index, (title, channel) in enumerate([
            ("Boruto Opening 3 (HD)", "Obito Uchiha"),
            ("Boruto Opening 7", "vizmedia"),
            ("Boruto Opening 11", "RANDOM")]):
            y = index * 70
            items.extend([(title, 8, y, 250, 14), (channel, 8, y + 25, 150, 14)])
        self.assertEqual(text_from_ocr(ocr_result(items), (700, 220)), [
            "Boruto Opening 3 (HD)", "Boruto Opening 7", "Boruto Opening 11"])

    def test_already_formatted_queries_and_year_titles_are_preserved(self):
        lines = ["Adele - Hello", "Shakira - Antologia", "1979"]
        self.assertEqual(organize_playlist_text("\n".join(lines)), lines)
        self.assertEqual(organize_playlist_text("Jay-Z - 4:44"), ["Jay-Z - 4:44"])
        self.assertEqual(clean_queries("Jay-Z - 4:44\n4:44"), ["Jay-Z - 4:44", "4:44"])

    def test_video_followed_by_another_named_song_is_not_removed(self):
        text = "Boruto Opening 3\nEve - Gunjo Sanka"
        self.assertEqual(organize_playlist_text(text), text.splitlines())

    def test_ordinary_lines_are_not_paired_by_proximity_alone(self):
        items = [(title, 20, index * 36, 230, 24) for index, title in enumerate([
            "Adele - Hello", "Shakira - Antologia", "Eve - Gunjo Sanka", "LONGMAN - spiral"])]
        self.assertEqual(text_from_ocr(ocr_result(items)), [item[0] for item in items])


if __name__ == "__main__":
    unittest.main(verbosity=2)
