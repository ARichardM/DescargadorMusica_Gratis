"""Reproductor integrado: identidad, errores y servidor local sin acceso a archivos."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from reproductor_video import video_id, player_error, player_page, make_player_server, run_player, PlayerJob


class PlayerTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Requiere Node.js para ejecutar los controles JavaScript")
    def test_timeline_seeking_and_play_pause_with_real_page_script(self):
        page = player_page('abcdefghijk', 'Título', 'http://127.0.0.1:8888', '/token')
        script = re.search(r'<script>(.*?)</script>', page, re.DOTALL)[1]
        result = subprocess.run([shutil.which("node"), str(Path(__file__).parent / "player_controls.test.js")],
                                input=script, text=True, encoding="utf-8", capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_video_urls_are_validated(self):
        for url in ('https://www.youtube.com/watch?v=abcdefghijk', 'https://music.youtube.com/watch?v=abcdefghijk',
                    'https://youtu.be/abcdefghijk'):
            self.assertEqual(video_id(url), 'abcdefghijk')
        for url in ('file:///C:/secret', 'https://example.com/watch?v=abcdefghijk',
                    'https://youtube.com.evil.test/watch?v=abcdefghijk', 'https://youtube.com/watch?v=bad',
                    'https://user:pass@youtube.com/watch?v=abcdefghijk'):
            with self.assertRaises(ValueError):
                video_id(url)

    def test_page_escapes_title_and_keeps_player_controls_and_origin(self):
        page = player_page('abcdefghijk', '</h1><script>bad()</script>', 'http://127.0.0.1:8888', '/token', autoplay=False)
        self.assertNotIn('</h1><script>bad()', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertIn('strict-origin-when-cross-origin', page)
        self.assertIn('controls:1', page)
        self.assertIn('onAutoplayBlocked', page)
        self.assertIn('"autoplay": false', page)
        self.assertIn('http://127.0.0.1:8888', page)
        self.assertNotIn('pywebview.api', page)

    def test_errors_distinguish_missing_and_embedding_disabled(self):
        self.assertIn('privado', player_error(100))
        self.assertIn('propietario', player_error(101))
        self.assertIn('propietario', player_error(150))
        self.assertIn('identificación', player_error(153))
        self.assertIn('conexión', player_error(-1))

    def test_local_server_only_serves_player_and_accepts_origin_checked_events(self):
        events = []
        server, url = make_player_server('abcdefghijk', 'Título', events.append, autoplay=False)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = 'http://' + urlsplit(url).netloc
        try:
            with urlopen(url, timeout=2) as response:
                self.assertIn('Título', response.read().decode('utf-8'))
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
            for path in ('/cookies.txt', '/C:/secret', '/../requirements.txt'):
                with self.assertRaises(HTTPError) as error:
                    urlopen(origin + path, timeout=2)
                self.assertEqual(error.exception.code, 404)
            payload = json.dumps(dict(status='error', code=101)).encode()
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(url + '/event', data=payload, headers={'Origin': 'https://example.com'}), timeout=2)
            self.assertEqual(error.exception.code, 403)
            with urlopen(Request(url + '/event', data=payload, headers={'Origin': origin}), timeout=2) as response:
                self.assertEqual(response.status, 204)
            self.assertIn('propietario', events[0]['text'])
            with self.assertRaises(HTTPError):
                urlopen(Request(url + '/event', data=b'{bad json}', headers={'Origin': origin}), timeout=2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_runtime_has_downloads_disabled_and_no_cookie_import(self):
        fake_webview = SimpleNamespace(settings={}, create_window=Mock(), start=Mock())
        output = io.StringIO()
        with patch.dict('sys.modules', {'webview': fake_webview}), redirect_stdout(output):
            result = run_player(dict(url='https://www.youtube.com/watch?v=abcdefghijk', title='Título'))
        self.assertEqual(result, 0)
        self.assertFalse(fake_webview.settings['ALLOW_DOWNLOADS'])
        self.assertFalse(fake_webview.settings['ALLOW_FILE_URLS'])
        self.assertTrue(fake_webview.start.call_args.kwargs['private_mode'])
        self.assertIsNone(fake_webview.create_window.call_args.kwargs.get('js_api'))
        self.assertTrue(fake_webview.create_window.call_args.kwargs['url'].startswith('http://127.0.0.1:'))

    def test_missing_webview_and_cancelled_job_are_handled(self):
        output = io.StringIO()
        with patch.dict('sys.modules', {'webview': None}), redirect_stdout(output):
            result = run_player(dict(url='https://www.youtube.com/watch?v=abcdefghijk'))
        self.assertEqual(result, 1)
        self.assertIn('WebView2', json.loads(output.getvalue())['text'])
        job = PlayerJob()
        job.cancel()
        with patch('reproductor_video.subprocess.Popen') as popen:
            job.run(dict(url='https://www.youtube.com/watch?v=abcdefghijk'))
        popen.assert_not_called()
        self.assertEqual(job.events.get_nowait()['event'], 'player_done')


if __name__ == '__main__':
    unittest.main()
