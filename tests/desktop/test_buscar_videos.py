"""Búsqueda con miniaturas, escucha integrada y selección sin descarga automática."""

from contextlib import redirect_stdout
import gc
import io
import json
import queue
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image

import canciones
import descargador_gui as backend
from buscar_videos import (VideoSearchDialog, ThumbnailJob, ThumbnailRedirect, load_thumbnail,
                           thumbnail_url_allowed, duration_label, MAX_THUMBNAIL_BYTES)


def candidate(index=0):
    identifier = ('abcdefghijk', 'lmnopqrstuv')[index]
    return dict(title=('Eve - 心海', 'Artista - Canción')[index], channel='Canal oficial', duration=265 + index,
                url='https://www.youtube.com/watch?v=' + identifier,
                thumbnail='https://i.ytimg.com/vi/' + identifier + '/mqdefault.jpg')


class SearchBackendTests(unittest.TestCase):
    def test_ten_results_use_public_thumbnail_and_do_not_download_media(self):
        downloader = Mock()
        downloader.extract_info.return_value = dict(entries=[dict(id='abcdefghijk', title='Título', channel='Canal', duration=270)])
        results = canciones.search_candidates('Eve Shinkai', downloader, limit=10, include_thumbnail=True)
        downloader.extract_info.assert_called_once_with('ytsearch10:Eve Shinkai', download=False)
        self.assertEqual(results[0]['thumbnail'], 'https://i.ytimg.com/vi/abcdefghijk/mqdefault.jpg')

    def test_browse_worker_emits_results_with_thumbnails(self):
        downloader = Mock()
        downloader.extract_info.return_value = dict(entries=[dict(id='abcdefghijk', title='Título', duration=120)])
        output = io.StringIO()
        with patch('yt_dlp.YoutubeDL') as factory, redirect_stdout(output):
            factory.return_value.__enter__.return_value = downloader
            canciones.run_import_worker(dict(task='browse', query='Artista título'))
        result = next(json.loads(line) for line in output.getvalue().splitlines() if json.loads(line)['event'] == 'search_result')
        self.assertIn('thumbnail', result['candidates'][0])
        downloader.extract_info.assert_called_once_with('ytsearch10:Artista título', download=False)

    def test_empty_or_excessive_search_does_not_query_youtube(self):
        for query in (' ', 'a' * 301):
            with patch('yt_dlp.YoutubeDL') as factory, redirect_stdout(io.StringIO()):
                self.assertEqual(canciones.run_import_worker(dict(task='browse', query=query)), 1)
            factory.assert_not_called()

    def test_thumbnail_urls_reject_other_hosts_files_credentials_and_ports(self):
        self.assertTrue(thumbnail_url_allowed(candidate()['thumbnail']))
        for url in ('file:///C:/secret', 'https://example.com/image.jpg', 'http://i.ytimg.com/x',
                    'https://i.ytimg.com.evil.test/x', 'https://user:pass@i.ytimg.com/x',
                    'https://i.ytimg.com:8888/x', 'https://i.ytimg.com:bad/x'):
            self.assertFalse(thumbnail_url_allowed(url))
        with self.assertRaises(ValueError):
            ThumbnailRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com/evil')

    def test_thumbnail_decodes_and_resizes_without_creating_tk_objects(self):
        image = Image.new('RGB', (320, 180), 'blue')
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        response = Mock()
        response.geturl.return_value = candidate()['thumbnail']
        response.read.return_value = buffer.getvalue()
        with patch('buscar_videos.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value = response
            picture = load_thumbnail(candidate()['thumbnail'])
        self.assertEqual(picture.size, (160, 90))
        picture.close()
        image.close()
        response.read.return_value = b'x' * (MAX_THUMBNAIL_BYTES + 1)
        with patch('buscar_videos.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value = response
            with self.assertRaisesRegex(ValueError, 'tamaño'):
                load_thumbnail(candidate()['thumbnail'])

    def test_thumbnail_failures_do_not_abort_other_results(self):
        events = queue.Queue()
        job = ThumbnailJob(events, 8)
        image = Image.new('RGB', (160, 90))
        with patch('buscar_videos.load_thumbnail', side_effect=[OSError('Error CDN'), image]):
            job.run([candidate(), candidate(1)])
        first, second = events.get_nowait(), events.get_nowait()
        self.assertEqual(first['error'], 'Error CDN')
        self.assertIsNone(first['image'])
        self.assertIs(second['image'], image)
        image.close()
        job.cancel()
        with patch('buscar_videos.load_thumbnail') as load:
            job.run([candidate()])
        load.assert_not_called()

    def test_duration_labels_support_long_videos(self):
        self.assertEqual(duration_label(3661), '1:01:01')
        self.assertEqual(duration_label(265), '4:25')
        for value in (None, -1, 'bad', float('inf')):
            self.assertEqual(duration_label(value), 'Duración desconocida')


class VisualSearchTests(unittest.TestCase):
    def setUp(self):
        self.root = backend.launch_gui()
        self.root.withdraw()
        self.received = []
        self.thumb_patch = patch('buscar_videos.ThumbnailJob.run')
        self.thumb_patch.start()
        self.dialog = VideoSearchDialog(self.root, lambda urls: self.received.extend(urls))
        self.dialog.withdraw()

    def tearDown(self):
        self.root.destroy()
        self.thumb_patch.stop()
        self.root = self.dialog = None
        gc.collect()

    def poll(self):
        if self.dialog.poll_timer:
            self.dialog.after_cancel(self.dialog.poll_timer)
        self.dialog.poll_events()

    def results(self):
        self.dialog.show_results([candidate(), candidate(1)])

    def test_cards_have_titles_and_choices_and_add_only_checked(self):
        self.results()
        self.assertEqual(len(self.dialog.rows), 2)
        self.assertIn('心海', self.dialog.rows[0]['title']['text'])
        self.dialog.rows[1]['selected'].set(True)
        self.dialog.update_choices()
        self.assertEqual(self.dialog.choice_var.get(), '1 elegido')
        self.dialog.add_selected()
        self.assertEqual(self.received, [candidate(1)['url']])
        self.assertFalse(self.root.running)

    def test_typing_does_not_query_and_explicit_search_uses_worker(self):
        with patch('buscar_videos.ImportJob.run') as run:
            self.dialog.query_var.set('Eve Shinkai')
            self.root.update()
            run.assert_not_called()
            self.dialog.start_search()
            self.assertTrue(self.dialog.busy)
        self.assertEqual(run.call_args.args[0]['task'], 'browse')
        self.assertEqual(run.call_args.args[0]['query'], 'Eve Shinkai')
        self.dialog.handle_event(dict(event='job_done', cancelled=True))
        self.assertFalse(self.dialog.busy)

    def test_playback_is_integrated_and_never_adds_or_downloads(self):
        self.results()
        fake = SimpleNamespace(events=queue.Queue(), run=Mock(), cancel=Mock())
        with patch('buscar_videos.PlayerJob', return_value=fake), patch('buscar_videos.webbrowser.open') as browser:
            self.dialog.preview(0)
            browser.assert_not_called()
        self.assertEqual(fake.run.call_args.args[0]['url'], candidate()['url'])
        self.assertFalse(self.received)
        self.assertFalse(self.root.running)
        fake.events.put(dict(event='player', status='error', text='El propietario no permite reproducción integrada.'))
        fake.events.put(dict(event='player_done', cancelled=False))
        self.poll()
        self.assertIn('no permite', self.dialog.player_status_var.get())

    def test_browser_is_only_opened_on_explicit_alternative_click(self):
        self.results()
        with patch('buscar_videos.webbrowser.open', return_value=True) as browser:
            self.dialog.open_browser(0)
        browser.assert_called_once_with(candidate()['url'])
        self.assertFalse(self.received)

    def test_thumbnails_update_on_tk_thread_and_stale_generation_is_ignored(self):
        self.results()
        picture = Image.new('RGB', (160, 90), 'blue')
        self.dialog.thumbnail_events.put(dict(generation=self.dialog.generation, index=0, image=picture, error=''))
        self.poll()
        self.assertIn(0, self.dialog.photos)
        self.dialog.clear_results()
        old = Image.new('RGB', (160, 90), 'red')
        self.dialog.thumbnail_events.put(dict(generation=self.dialog.generation - 1, index=0, image=old, error=''))
        self.poll()
        self.assertFalse(self.dialog.photos)

    def test_empty_results_and_blocked_search_show_real_reason(self):
        self.dialog.job = canciones.ImportJob()
        self.dialog.set_busy(True)
        self.dialog.handle_event(dict(event='search_result', candidates=[], reason='HTTP 429: espera antes de reintentar.', failed=True))
        self.dialog.handle_event(dict(event='job_done', cancelled=False))
        self.assertIn('429', self.dialog.status_var.get())
        self.assertEqual(str(self.dialog.add_button['state']), 'disabled')

    def test_search_and_footer_fit_in_small_window(self):
        self.root.deiconify()
        self.dialog.deiconify()
        self.dialog.geometry('740x560')
        self.results()
        self.root.update()
        self.assertTrue(self.dialog.search_button.winfo_ismapped())
        self.assertTrue(self.dialog.add_button.winfo_ismapped())
        self.assertLess(self.dialog.add_button.winfo_rooty() + self.dialog.add_button.winfo_height(),
                        self.dialog.winfo_rooty() + self.dialog.winfo_height())

    def test_close_cancels_active_search_before_destroying(self):
        self.dialog.job = canciones.ImportJob()
        self.dialog.set_busy(True)
        self.dialog.close()
        self.assertTrue(self.dialog.closing)
        self.assertTrue(self.dialog.winfo_exists())
        self.dialog.handle_event(dict(event='job_done', cancelled=True))
        self.poll()
        self.assertFalse(self.dialog.winfo_exists())


if __name__ == '__main__':
    unittest.main()
