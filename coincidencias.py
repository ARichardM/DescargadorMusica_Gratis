"""Comparación local de resultados; las puntuaciones no son probabilidades."""

from dataclasses import dataclass
from difflib import SequenceMatcher
import math
import re
import unicodedata


def normalize(text):
    text = unicodedata.normalize("NFKC", str(text or "")).casefold()
    # Elimina acentos latinos, pero conserva dakuten/handakuten japoneses.
    text = "".join("".join(part for part in unicodedata.normalize("NFD", char)
                           if not unicodedata.combining(part))
                   if "LATIN" in unicodedata.name(char, "") else char for char in text)
    return " ".join("".join(char if char.isalnum() else " "
                            for char in text if not unicodedata.combining(char)).split())


DECORATIONS = re.compile(
    r"\b(?:official\s+(?:music\s+)?(?:video|audio)|music\s+video|"
    r"official|lyrics?|lyric\s+video|hd|hq|4k|1080p|720p)\b")
VERSIONS = (r"\blive\b|\ben vivo\b", r"\bcover\b", r"\bkaraoke\b|\binstrumental\b",
            r"\bremix\b", r"\bslowed\b|\breverb\b", r"\bnightcore\b|\bsped up\b",
            r"\bacoustic\b|\bacustic[oa]\b", r"\breaction\b|\btutorial\b")


def content(text):
    return " ".join(DECORATIONS.sub(" ", normalize(text)).split())


def similarity(wanted, found):
    if not wanted or not found:
        return 0.0
    sequence = SequenceMatcher(None, wanted, found, autojunk=False).ratio()
    left, right = set(wanted.split()), set(found.split())
    overlap = len(left & right)
    token_score = 2 * overlap / (len(left) + len(right))
    return max(sequence, token_score)


def seconds(value):
    try:
        if isinstance(value, str) and ":" in value:
            parts = value.split(":")
            if len(parts) not in (2, 3):
                return None
            total = 0
            for part in parts:
                total = total * 60 + int(part)
        else:
            total = float(value)
        return total if math.isfinite(total) and total > 0 else None
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class Match:
    exact: bool
    score: float
    full_exact: bool = False


def score_candidate(query, candidate, *, title="", artist="", duration=""):
    """El título completo exacto tiene prioridad; artista y tiempo desempatan."""
    wanted_full = normalize(query)
    found_full = normalize(candidate.get("title"))
    wanted_title = content(title or query)
    found_title = content(candidate.get("title"))
    wanted_artist = normalize(artist)
    channel = normalize(candidate.get("channel"))
    # Permite tanto «artista - título» como «título - artista».
    if wanted_artist:
        found_title = " ".join(re.sub(r"(?<!\w)" + re.escape(wanted_artist) + r"(?!\w)",
                                     " ", found_title).split())
    artist_match = bool(wanted_artist and re.search(
        r"(?<!\w)" + re.escape(wanted_artist) + r"(?!\w)", found_full + " " + channel))
    name_score = max(similarity(wanted_title, found_title),
                     similarity(content(query), content(candidate.get("title"))))
    score = name_score * .80
    if wanted_artist:
        score += .20 if artist_match else -.15
    wanted_seconds, found_seconds = seconds(duration), seconds(candidate.get("duration"))
    if wanted_seconds and found_seconds:
        difference = abs(wanted_seconds - found_seconds)
        score += .10 * max(-1, 1 - difference / max(12, wanted_seconds * .12))
    for variant in VERSIONS:
        if re.search(variant, found_full) and not re.search(variant, wanted_full):
            score -= .18
    full_exact = bool(wanted_full and wanted_full == found_full)
    title_exact = bool(wanted_title and wanted_title == found_title)
    return Match(full_exact or (title_exact and (not wanted_artist or artist_match)), score, full_exact)


def best_candidate(query, candidates, **metadata):
    """Índice y comparación de la mejor opción; empates conservan el orden de búsqueda."""
    if not candidates:
        return None
    matches = [score_candidate(query, candidate, **metadata) for candidate in candidates]
    index = max(range(len(matches)), key=lambda i: (matches[i].full_exact, matches[i].score))
    return index, matches[index]
