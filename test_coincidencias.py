"""Selección exacta, aproximada y desempates sin acceso a Internet."""

import unittest

from coincidencias import best_candidate, normalize, seconds


def candidate(title, channel="", duration=None):
    return dict(title=title, channel=channel, duration=duration)


class MatchingTests(unittest.TestCase):
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
