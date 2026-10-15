"""Control de streaming, búsqueda temporal y transporte de comandos de audio."""

from contextlib import redirect_stdout
import io
import json
import queue
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from reproductor_audio import (AudioJob, FRAME_BYTES, FRAMES, RATE, decoder_command,
                               play_audio, resolve_audio, run_audio)


class AudioEngineTests(unittest.TestCase):
    def playback(self, commands=None, on_write=None, code=0):
        commands = commands or queue.Queue()
        stream = Mock(active=False, write_available=FRAMES)
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        stream.start.side_effect = lambda: setattr(stream, "active", True)
        stream.abort.side_effect = lambda: setattr(stream, "active", False)
        stream.stop.side_effect = lambda: setattr(stream, "active", False)
        stream.write.side_effect = on_write
        decoders = []

        def decoder(*args):
            chunks = queue.Queue()
            chunks.put(bytes(FRAMES * FRAME_BYTES))
            chunks.put(b"")
            result = SimpleNamespace(chunks=chunks, process=Mock(), close=Mock(), position=args[2])
            result.process.wait.return_value = code
            decoders.append(result)
            return result

        events = []
        play_audio(dict(url="https://media.example/audio", duration=180), commands, events.append,
                   ffmpeg="ffmpeg", stream_factory=Mock(return_value=stream), decoder_factory=decoder)
        return events, stream, decoders

    def test_duration_progress_and_end_follow_decoded_samples(self):
        events, stream, decoders = self.playback()
        self.assertEqual(events[-1]["status"], "ended")
        self.assertAlmostEqual(events[-1]["position"], FRAMES / RATE)
        stream.write.assert_called_once()
        decoders[0].close.assert_called_once()
        stream.__exit__.assert_called_once()

    def test_pause_resume_and_seek_restart_decoder_at_clamped_position(self):
        commands = queue.Queue()
        for action in (dict(action="pause"), dict(action="seek", position=500), dict(action="resume")):
            commands.put(action)
        events, stream, decoders = self.playback(commands)
        self.assertEqual([event["status"] for event in events[:3]], ["paused", "paused", "loading"])
        self.assertAlmostEqual(decoders[1].position, 179.95)
        self.assertEqual(events[1]["position"], 179.95)
        self.assertAlmostEqual(events[-1]["position"], 179.95 + FRAMES / RATE)
        self.assertEqual(stream.write.call_count, 1)  # No se consumen bloques durante la pausa.
        self.assertTrue(all(d.close.called for d in decoders))

    def test_stop_releases_decoder_and_output_without_consuming_audio(self):
        commands = queue.Queue()
        commands.put(dict(action="stop"))
        events, stream, decoders = self.playback(commands)
        self.assertFalse(events)
        stream.write.assert_not_called()
        decoders[0].close.assert_called_once()
        stream.__exit__.assert_called_once()

    def test_invalid_seek_is_ignored_and_decoder_failures_are_reported(self):
        commands = queue.Queue()
        commands.put(dict(action="seek", position=float("nan")))
        commands.put(dict(action="seek", position="invalid"))
        events, _, decoders = self.playback(commands)
        self.assertEqual(len(decoders), 1)
        self.assertEqual(events[-1]["status"], "ended")
        with self.assertRaisesRegex(RuntimeError, "conexión"):
            self.playback(code=1)

    def test_decoder_seeks_before_input_and_never_requests_video_or_files(self):
        command = decoder_command("ffmpeg", dict(url="https://media.example/audio", headers={
            "User-Agent": "test", "Injected": "bad\r\nheader"}), 42.5)
        self.assertLess(command.index("-ss"), command.index("-i"))
        self.assertIn("42.500", command)
        self.assertIn("-vn", command)
        self.assertEqual(command[-1], "pipe:1")
        self.assertIn("User-Agent: test\r\n", command)
        self.assertNotIn("Injected", " ".join(command))

    def test_resolver_only_extracts_selected_video_with_configured_cookies(self):
        info = dict(url="https://media.example/audio", duration=200, http_headers={"User-Agent": "test"})
        downloader = Mock()
        downloader.__enter__ = Mock(return_value=downloader)
        downloader.__exit__ = Mock(return_value=False)
        downloader.extract_info.return_value = info
        with patch("yt_dlp.YoutubeDL", return_value=downloader) as factory:
            source = resolve_audio(dict(url="https://youtu.be/abcdefghijk", cookies="private.txt"))
        downloader.extract_info.assert_called_once_with("https://www.youtube.com/watch?v=abcdefghijk", download=False)
        self.assertTrue(factory.call_args.args[0]["skip_download"])
        self.assertEqual(factory.call_args.args[0]["cookiefile"], "private.txt")
        self.assertEqual(source["duration"], 200)

    def test_worker_reports_missing_ffmpeg_without_attempting_network(self):
        output = io.StringIO()
        with patch("reproductor_audio.backend.find_ffmpeg", return_value=None), \
                patch("reproductor_audio.resolve_audio") as resolve, \
                patch("sys.stdin", io.StringIO("")), redirect_stdout(output):
            self.assertEqual(run_audio({}), 1)
        event = json.loads(output.getvalue())
        self.assertEqual(event["status"], "error")
        self.assertIn("FFmpeg", event["text"])
        resolve.assert_not_called()

    def test_job_transports_commands_before_start_and_keeps_terminal_error(self):
        job = AudioJob()
        job.command("seek", position=55)
        written = []
        command_sent = threading.Event()
        process = Mock()

        def write(line):
            written.append(line)
            if "action" in json.loads(line):
                command_sent.set()

        process.stdin.write.side_effect = write
        process.stdout = iter([json.dumps(dict(event="audio", status="error", text="Bloqueado")) + "\n"])
        process.wait.return_value = 1
        process.poll.return_value = 1
        # El lector de comandos puede correr antes de salir; usamos un stdout que permite cerrarse.
        class Lines:
            def __iter__(self):
                if not command_sent.wait(timeout=2):
                    raise TimeoutError("El comando no llegó al trabajador")
                yield json.dumps(dict(event="audio", status="error", text="Bloqueado")) + "\n"
            def close(self): pass
        process.stdout = Lines()
        with patch("reproductor_audio.subprocess.Popen", return_value=process):
            job.run(dict(url="https://youtu.be/abcdefghijk"))
        events = list(job.events.queue)
        self.assertEqual([e["event"] for e in events], ["audio", "audio_done"])
        self.assertEqual(events[0]["text"], "Bloqueado")
        self.assertEqual(json.loads(written[0])["url"], "https://youtu.be/abcdefghijk")
        self.assertIn(dict(action="seek", position=55), [json.loads(line) for line in written])
        process.stdin.close.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
