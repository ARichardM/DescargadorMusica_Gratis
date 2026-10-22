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
    review_reason: str = ""
    raw_text: str = ""

    @property
    def query(self):
        return song_query(self.title, self.artist)


@dataclass
class ParsedPlaylist:
    songs: list[ImportedSong]
    timed_blocks: int
    warnings: list[str] = field(default_factory=list)


JOINER = r"(?:[,，、&]|(?:and|y|feat\.?|ft\.?)(?=\s|$))"


def split_song_fields(body):
    """Lee título, artistas conectados explícitamente y un álbum opcional.

    Los separadores pueden ocupar su propia línea o estar unidos a un nombre.
    No adivina si dos líneas sin separador son artistas distintos.
    """
    if len(body) < 2 or (len(body) == 2 and all(" - " in line for line in body)):
        return None
    title, performer = body[:2]
    if not any(char.isalnum() for char in performer):
        return None
    cursor = 2
    while cursor < len(body):
        line = body[cursor]
        if re.fullmatch(JOINER, line, re.IGNORECASE):
            if cursor + 1 >= len(body) or not any(char.isalnum() for char in body[cursor + 1]):
                return None
            performer += (", " if line in (",", "，", "、") else f" {line} ") + body[cursor + 1]
            cursor += 2
        # En una línea con texto, solo los símbolos son separadores inequívocos:
        # un álbum puede llamarse «And Justice for All» o «Y ahora».
        elif re.match(r"^[,，、&]\s*\S", line):
            performer += ("" if line.startswith((",", "，", "、")) else " ") + line
            cursor += 1
        elif re.search(r"(?:[,，、&]|\s(?:and|y|feat\.?|ft\.?))$", performer, re.IGNORECASE):
            performer += " " + line
            cursor += 1
        else:
            break
    if re.search(r"(?:[,，、&]|\s(?:and|y|feat\.?|ft\.?))$", performer, re.IGNORECASE):
        return None
    if len(body) - cursor > 1:
        return None
    return title, performer, body[cursor] if cursor < len(body) else ""


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
        return split_song_fields(body) is not None

    def split_parts(parts):
        flat = [line for part in parts for line in part]
        # Los saltos en blanco también pueden separar nombres de una colaboración.
        explicit_heading = len(parts) > 1 and all(len(part) == 1 and part[0].startswith("#") for part in parts[:-1])
        if plausible(flat) and not explicit_heading:
            return [], flat
        if not plausible(flat) and len(parts) > 1:
            headings = all(len(part) == 1 and (part[0].startswith("#")
                           or VIDEO_TITLE.search(part[0]) or VIDEO_METADATA.search(part[0])) for part in parts[:-1])
            if not headings:
                return [], flat
        return parts[:-1], parts[-1]

    # Un bloque roto no debe convertir el resto de una lista reconocible en consultas por línea.
    def recognizable(parts):
        flat = [line for part in parts for line in part]
        return (plausible(flat) or plausible(parts[-1])
                or (len(flat) >= 4 and not all(" - " in line for line in flat)))

    # Un tiempo justo después del título (antes del artista) es otro formato,
    # habitual en OCR: no confundirlo con el exportado de duración final.
    if not frames or not recognizable(frames[0][0]):
        return None

    songs, warnings = [], []
    def make_song(body, duration=""):
        title, performer, album = split_song_fields(body)
        is_video = not album and bool(VIDEO_TITLE.search(title) or VIDEO_METADATA.search(title))
        return ImportedSong(title=title, artist=video_artist(title) if is_video else performer,
                            album=album, duration=duration, uploader=performer if is_video else "")

    def keep_extra(lines):
        for line in lines:
            line = re.sub(r"^#{1,6}\s+", "", line).strip()
            if line:
                songs.append(ImportedSong(title=line, structured=False))

    def keep_ambiguous(lines, duration=""):
        reason = "No se pudieron separar título, artistas y álbum. Revisa el texto original y corrige esta fila."
        songs.append(ImportedSong(title=lines[0], duration=duration, review_reason=reason,
                                  raw_text="\n".join(lines)))
        warnings.append(reason)

    for parts, duration in frames:
        # Por ejemplo, un título pegado antes de la lista no se fusiona con la primera canción.
        prefixes, body = split_parts(parts)
        if not plausible(body):
            # Conservar TODO el bloque en una sola fila, nunca buscar artistas/álbumes sueltos.
            flat = [line for part in parts for line in part]
            keep_ambiguous(flat, duration)
            continue
        for prefix in prefixes:
            keep_extra(prefix)
        songs.append(make_song(body, duration))
    for trailing in paragraphs:
        if plausible(trailing):
            songs.append(make_song(trailing))
        else:
            keep_ambiguous(trailing)
        warnings.append("Se conservó texto final sin duración para revisión.")
    return ParsedPlaylist(songs, len(frames), warnings)
