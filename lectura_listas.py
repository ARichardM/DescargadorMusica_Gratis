"""Organiza capturas de listas musicales sin adivinar títulos o artistas ausentes."""

from dataclasses import dataclass
import re
from statistics import median
import unicodedata


DURATION = re.compile(r"^(?:\d{1,2}:)?\d{1,3}:[0-5]\d$")
SEPARATOR = re.compile(r"\s*[·•●]\s*")
VIDEO_TITLE = re.compile(r"opening|ending|creditless|\bPV\b|TV\s*アニメ", re.IGNORECASE)
VIDEO_METADATA = re.compile(
    r"\b(?:OP|ED|OST|AMV|MAD|MV|HD|FPS|4K)\b|music video|ノンクレジット|ノン.?クレジット|remake|extended theme",
    re.IGNORECASE,
)


def video_artist(title):
    """Extrae créditos explícitos; conserva el título completo para buscar su versión."""
    if not (VIDEO_TITLE.search(title) or VIDEO_METADATA.search(title) or "|" in title):
        return ""
    credit = re.search(r"\bby\s+([^|]+)", title, re.IGNORECASE)
    if credit:
        artist = credit[1].strip(" \t\"“”「」")
        artist = re.sub(r"\s*[\[(](?:official\b|lyrics?\b|HD\b|4K\b).*", "", artist,
                        flags=re.IGNORECASE).strip()
        # «Stand by Me» y «By Your Side» son títulos, no créditos.
        if (artist and artist.casefold() not in {"me", "you", "us", "my side", "your side", "myself"}
                and not artist.endswith(("…", "..."))):
            return artist
    dated = re.search(r"\s-\s([^|]+?)\s*\((?:19|20)\d{2}\)(?:\s|$)", title)
    return dated[1].strip() if dated else ""


def song_query(title, artist=""):
    if artist and not re.search(r"(?<!\w)" + re.escape(artist) + r"(?!\w)", title, re.IGNORECASE):
        return f"{artist} - {title}"
    return title


def tidy_ocr_line(text):
    text = " ".join(unicodedata.normalize("NFKC", str(text)).split())
    if DURATION.fullmatch(text):
        return ""
    duration = re.search(r"\s+(?:\d{1,2}:)?\d{1,3}:[0-5]\d$", text)
    if duration and not text[:duration.start()].rstrip().endswith(("-", "–", "—", ":")):
        text = text[:duration.start()]
    text = re.sub(r"^\d{1,3}[.)]\s+", "", text)
    original = text
    text = text.strip(" \t-|–—·•")
    if not text or not any(char.isalnum() for char in text):
        return ""
    # Los controles o iconos suelen producir fragmentos de un carácter seguidos de un guion.
    if len(text) == 1 and original.rstrip().endswith("-"):
        return ""
    return text


def artist_line(text):
    parts = SEPARATOR.split(text, maxsplit=1)
    return parts[0].strip(" -") if len(parts) == 2 and parts[0].strip(" -") else None


def combine_title_artist(title, metadata):
    artist = artist_line(metadata)
    if not artist:
        return title
    key = lambda value: re.sub(r"[\W_]+", "", value.casefold())
    if key(title).startswith(key(artist)):
        return title
    return f"{artist} - {title}"


def unique_lines(lines):
    result, seen = [], set()
    for line in lines:
        if line and line.casefold() not in seen:
            result.append(line)
            seen.add(line.casefold())
    return result


def organize_playlist_text(text, *, uploaders=None):
    """Limpieza explícita del texto pegado: tiempos, título/subtítulo y canales de openings."""
    lines = [cleaned for line in text.splitlines() if (cleaned := tidy_ocr_line(line))]
    result = []
    index = 0
    while index < len(lines):
        title = lines[index]
        if index + 1 < len(lines) and not artist_line(title):
            subtitle = lines[index + 1]
            if artist_line(subtitle):
                result.append(combine_title_artist(title, subtitle))
                index += 2
                continue
            if (VIDEO_TITLE.search(title) and not VIDEO_TITLE.search(subtitle)
                    and " - " not in subtitle and len(subtitle) <= 50):
                # Un canal de subida no es necesariamente el intérprete de la canción.
                if uploaders is not None:
                    uploaders[title.casefold()] = subtitle
                result.append(title)
                index += 2
                continue
        result.append(title)
        index += 1
    return unique_lines(result)


@dataclass
class Block:
    text: str
    left: float
    top: float
    right: float
    bottom: float

    @property
    def middle(self):
        return (self.top + self.bottom) / 2

    @property
    def height(self):
        return max(1, self.bottom - self.top)


def get_blocks(result):
    texts, boxes = getattr(result, "txts", None), getattr(result, "boxes", None)
    if texts is None or boxes is None:
        return []
    blocks = []
    for text, box in zip(texts, boxes):
        xs, ys = [float(point[0]) for point in box], [float(point[1]) for point in box]
        blocks.append(Block(str(text), min(xs), min(ys), max(xs), max(ys)))
    return blocks


def main_column(blocks):
    """Busca una alineación repetida; no asume una anchura o un idioma concretos."""
    content = [block for block in blocks if len(tidy_ocr_line(block.text)) >= 4]
    if not content:
        return []
    tolerance = max(5, median(block.height for block in content) * 0.8)
    clusters = []
    for block in sorted(content, key=lambda item: item.left):
        cluster = next((cluster for cluster in clusters if abs(cluster[0].left - block.left) <= tolerance), None)
        if cluster is None:
            clusters.append([block])
        else:
            cluster.append(block)
    return max(clusters, key=lambda cluster: sum(min(len(block.text), 30) for block in cluster))


def playlist_crop_bounds(result, image_size):
    """Propone otra lectura centrada en el texto cuando hay una lista con tiempos a la derecha."""
    blocks = get_blocks(result)
    clocks = [block for block in blocks if DURATION.fullmatch(block.text.strip())]
    column = main_column(blocks)
    if len(column) < 4 or len(clocks) < 2:
        return None
    width, height = image_size
    anchor = median(block.left for block in column)
    font_height = median(block.height for block in column)
    clocks = [block for block in clocks if block.left > anchor + width * 0.45]
    if len(clocks) < 2:
        return None
    left = max(0, round(anchor - font_height * 0.6))
    right = min(width, round(min(block.left for block in clocks) - font_height))
    if right - left < width * 0.45 or (left == 0 and right == width):
        return None
    return left, 0, right, height


def rows_from_ocr(result, image_size=None):
    blocks = get_blocks(result)
    column = main_column(blocks)
    has_clocks = sum(bool(DURATION.fullmatch(block.text.strip())) for block in blocks) >= 2
    font_height = median([block.height for block in column] or [14])
    anchor = median([block.left for block in column] or [0])
    blocks = [Block(text, block.left, block.top, block.right, block.bottom)
              for block in blocks if (text := tidy_ocr_line(block.text))]
    # En una captura completa, excluye texto de las portadas situado a la izquierda.
    if has_clocks and len(column) >= 4:
        blocks = [block for block in blocks if block.left >= anchor - font_height * 0.7]
    if image_size:
        blocks = [block for block in blocks
                  if not (block.left > image_size[0] * 0.7 and len(block.text) <= 2)]
    rows = []
    for block in sorted(blocks, key=lambda item: (item.middle, item.left)):
        row = next((row for row in reversed(rows[-3:])
                    if abs(row[0].middle - block.middle) <= max(4, min(row[0].height, block.height) * 0.55)), None)
        if row is None:
            rows.append([block])
        else:
            row.append(block)
    rows = [Block(" - ".join(block.text for block in sorted(row, key=lambda item: item.left)),
                  min(block.left for block in row), min(block.top for block in row),
                  max(block.right for block in row), max(block.bottom for block in row)) for row in rows]
    return rows, has_clocks


def playlist_lines_from_ocr(result, image_size=None, *, uploaders=None):
    rows, has_clocks = rows_from_ocr(result, image_size)
    if not rows:
        texts = getattr(result, "txts", None)
        return organize_playlist_text("\n".join(texts or []), uploaders=uploaders)
    gaps = [second.middle - first.middle for first, second in zip(rows, rows[1:])]
    height = median(row.height for row in rows)
    short_gaps = [gap for gap in gaps if height * 0.8 < gap <= height * 2.3]
    long_gaps = [gap for gap in gaps if gap > height * 2.3]
    repeating_pairs = len(rows) >= 4 and len(short_gaps) >= 2 and bool(long_gaps)
    result_lines = []
    index = 0
    while index < len(rows):
        title = rows[index]
        if index + 1 < len(rows) and not artist_line(title.text):
            subtitle = rows[index + 1]
            close = 0 < subtitle.middle - title.middle <= max(title.height, subtitle.height) * 2.3
            aligned = abs(title.left - subtitle.left) <= max(title.height, subtitle.height)
            if close and aligned and artist_line(subtitle.text):
                result_lines.append(combine_title_artist(title.text, subtitle.text))
                index += 2
                continue
            if close and aligned and (has_clocks or repeating_pairs) and not VIDEO_TITLE.search(subtitle.text):
                # El canal se conserva aparte del intérprete para mostrarlo en la tabla.
                if uploaders is not None:
                    uploaders[title.text.casefold()] = subtitle.text
                result_lines.append(title.text)
                index += 2
                continue
        result_lines.append(title.text)
        index += 1
    return unique_lines(result_lines)
