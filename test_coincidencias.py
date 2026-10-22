"""Selección exacta, aproximada y desempates sin acceso a Internet."""

import unittest

from coincidencias import best_candidate, normalize, seconds


def candidate(title, channel="", duration=None):
    return dict(title=title, channel=channel, duration=duration)


class MatchingTests(unittest.TestCase):
    def test_bad_best_result_stays_visible_but_is_not_automatically_selected(self):
        for query, title, artist, result in (
                ('Dazy', 'Dazy', '', candidate('daisy bell')),
                ('Daft Punk - Get Lucky', 'Get Lucky', 'Daft Punk', candidate('Daft Punk - One More Time', 'Daft Punk')),
                ('Kygo - Happy Now', 'Happy Now', 'Kygo', candidate('Zedd - Happy Now', 'Zedd')),
                ('Alok - Jungle', 'Jungle', 'Alok', candidate('Alok WE2 | Tomorrowland 2026', 'Alok'))):
            with self.subTest(query=query):
                index, match = best_candidate(query, [result], title=title, artist=artist)
                self.assertEqual(index, 0)
                self.assertFalse(match.auto_select)
                self.assertTrue(match.review_reason)

    def test_automatic_selection_checks_version_and_duration_even_for_exact_title(self):
        for result in (candidate('Hello (Live)', 'Adele', 295), candidate('Hello', 'Adele', 90)):
            match = best_candidate('Adele - Hello', [result], title='Hello', artist='Adele', duration='4:55')[1]
            self.assertFalse(match.auto_select)
            self.assertTrue(match.review_reason)
        match = best_candidate('Adele - Hello Remix', [candidate('Adele - Hello', 'Adele')],
                               title='Hello Remix', artist='Adele')[1]
        self.assertFalse(match.auto_select)

    def test_reordered_collaboration_and_minor_typo_can_be_automatically_selected(self):
        match = best_candidate('Dazy & Nicky Youre - Sunroof', [candidate('Nicky Youre, dazy - Sunroof (Official Video)',
                              'Nicky Youre', 175)], title='Sunroof', artist='Dazy & Nicky Youre', duration='2:55')[1]
        self.assertTrue(match.auto_select)
        self.assertTrue(match.exact)
        self.assertTrue(best_candidate('Gunjo Sanka', [candidate('Gunjou Sanka')])[1].auto_select)
        self.assertFalse(best_candidate('Hello', [{}])[1].auto_select)

    def test_exact_cyberpunk_with_unicode_quotes_wins_even_if_not_first(self):
        query = 'Cyberpunk: Edgerunners | “I Really Want to Stay At Your House” by Rosa Walton | Music Video'
        options = [candidate('ROSA WALTON - I REALLY WANT TO STAY AT YOUR HOUSE (LYRIC)'),
                   candidate(query.replace('“', '"').replace('”', '"'), 'Netflix'),
                   candidate('Cyberpunk Edgerunners OST Full | I Really Want To Stay At Your House')]
        index, match = best_candidate(query, options)
        self.assertEqual(index, 1)
        self.assertTrue(match.exact)

    def test_artist_and_reordered_name_with_decorations(self):
        options = [candidate('Hello', 'Otro cantante'),
                   candidate('Hello - Adele (Official Music Video)', 'AdeleVEVO')]
        index, match = best_candidate('Adele - Hello', options, title='Hello', artist='Adele')
        self.assertEqual(index, 1)
        self.assertTrue(match.exact)

    def test_unrequested_versions_are_penalized(self):
        options = [candidate('Adele - Hello (cover)', 'Adele', 295),
                   candidate('Hello (Official Audio)', 'Adele', 295),
                   candidate('Hello (Live)', 'Adele', 295)]
        self.assertEqual(best_candidate('Adele - Hello', options, title='Hello', artist='Adele')[0], 1)

    def test_requested_live_is_not_penalized(self):
        options = [candidate('Adele - Hello', 'Adele'), candidate('Adele - Hello Live', 'Adele')]
        self.assertEqual(best_candidate('Adele - Hello Live', options, title='Hello Live', artist='Adele')[0], 1)

    def test_duration_breaks_equal_title_ties(self):
        options = [candidate('Hello', 'Adele', 360), candidate('Hello', 'Adele', 295)]
        self.assertEqual(best_candidate('Adele - Hello', options, title='Hello', artist='Adele', duration='4:55')[0], 1)

    def test_fuzzy_fallback_is_not_just_first_result(self):
        index, match = best_candidate('Gunjo Sanka', [candidate('Unrelated Song'), candidate('Gunjou Sanka')])
        self.assertEqual(index, 1)
        self.assertFalse(match.exact)

    def test_normalization_keeps_japanese_and_accepts_accents(self):
        self.assertEqual(normalize('インフェルノ - Inferno'), 'インフェルノ inferno')
        self.assertEqual(normalize('CANCIÓN！'), 'cancion')
        self.assertEqual(normalize('グンジョウ'), 'グンジョウ')
        options = [candidate('Inferno'), candidate('インフェルノ - Inferno')]
        self.assertEqual(best_candidate('インフェルノ - Inferno', options)[0], 1)

    def test_full_exact_has_priority_over_duration_and_decorated_alternative(self):
        options = [candidate('Adele - Hello (Official Video)', 'Adele', 295),
                   candidate('Adele - Hello', 'Adele', 300)]
        self.assertEqual(best_candidate('Adele - Hello', options, title='Hello', artist='Adele', duration='4:55')[0], 1)

    def test_missing_metadata_empty_and_stable_ties(self):
        self.assertIsNone(best_candidate('Hello', []))
        self.assertEqual(best_candidate('Hello', [{}, {}])[0], 0)
        for value in (None, '', 'desconocida', 'nan', float('inf'), -1):
            self.assertIsNone(seconds(value))
        self.assertEqual(seconds('1:02:03'), 3723)


if __name__ == '__main__':
    unittest.main()
