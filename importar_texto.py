"""Reconoce listas copiadas con título, artista/canal, álbum y duración final."""

from dataclasses import dataclass, field
import re

from lectura_listas import DURATION, VIDEO_TITLE, VIDEO_METADATA, video_artist, song_query


@dataclass
class ImportedSong:
    title: str
    artist: str = ""
    album: str = ""
    duration: str = ""
    uploader: str = ""
    structured: bool = True

    @property
    def query(self):
        return song_query(self.title, self.artist)


@dataclass
class ParsedPlaylist:
    songs: list[ImportedSong]
    timed_blocks: int
    warnings: list[str] = field(default_factory=list)


def parse_exported_playlist(text):
    """Devuelve None si no hay evidencia suficiente del formato de lista exportada.

    Las líneas vacías separan párrafos y los tiempos cierran registros. La
    agrupación ocurre ANTES de quitar duplicados o duraciones. No ajusta el
    número de filas a un valor esperado y conserva entradas repetidas.
    """
    frames, paragraphs, paragraph = [], [], []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.lstrip("\ufeff").split())
        if not line:
            if paragraph:
                paragraphs.append(paragraph)
                paragraph = []
        elif DURATION.fullmatch(line):
            if paragraph:
                paragraphs.append(paragraph)
                paragraph = []
            if paragraphs:
                frames.append((paragraphs, line))
                paragraphs = []
        else:
            paragraph.append(line)
    if paragraph:
        paragraphs.append(paragraph)

    def plausible(body):
        return len(body) in (2, 3) and not (len(body) == 2 and all(" - " in line for line in body))

    def split_parts(parts):
        flat = [line for part in parts for line in part]
        if not plausible(parts[-1]) and plausible(flat):
            return [], flat
        return parts[:-1], parts[-1]

    valid = sum(plausible(split_parts(parts)[1]) for parts, _ in frames)
    if not frames or not plausible(split_parts(frames[0][0])[1]) or valid / len(frames) < 0.8:
        return None

    songs, warnings = [], []
    def make_song(body, duration=""):
        title, performer = body[:2]
        album = body[2] if len(body) == 3 else ""
        is_video = not album and bool(VIDEO_TITLE.search(title) or VIDEO_METADATA.search(title))
        return ImportedSong(title=title, artist=video_artist(title) if is_video else performer,
                            album=album, duration=duration, uploader=performer if is_video else "")

    def keep_extra(lines):
        for line in lines:
            line = re.sub(r"^#{1,6}\s+", "", line).strip()
            if line:
                songs.append(ImportedSong(title=line, structured=False))

    for parts, duration in frames:
        # Por ejemplo, un título pegado antes de la lista no se fusiona con la primera canción.
        prefixes, body = split_parts(parts)
        for prefix in prefixes:
            keep_extra(prefix)
        if not plausible(body):
            keep_extra(body)
            warnings.append("Un bloque incompleto o ambiguo se conservó para revisión.")
            continue
        songs.append(make_song(body, duration))
    for trailing in paragraphs:
        if plausible(trailing):
            songs.append(make_song(trailing))
        else:
            keep_extra(trailing)
        warnings.append("Se conservó texto final sin duración para revisión.")
    return ParsedPlaylist(songs, len(frames), warnings)
