"""Validación de playlist y motivos legibles, sin interfaz ni descargas."""

from urllib.parse import parse_qs, urlparse


def playlist_url(value):
    if not value.strip():
        return ""
    parsed = urlparse(value.strip())
    if parsed.scheme not in ("http", "https") or parsed.hostname not in (
            "youtube.com", "www.youtube.com", "music.youtube.com", "m.youtube.com"):
        raise ValueError("Pega un enlace de playlist de YouTube o YouTube Music.")
    identifier = parse_qs(parsed.query).get("list", [""])[0]
    if not identifier or not all(char.isascii() and (char.isalnum() or char in "_-") for char in identifier):
        raise ValueError("El enlace debe incluir el identificador de playlist (list=…).")
    return "https://www.youtube.com/playlist?list=" + identifier


def inspect_playlist(info):
    if not isinstance(info, dict) or "entries" not in info:
        raise ValueError("YouTube no devolvió las entradas de la playlist; no se pudo comprobar.")
    entries = list(info.get("entries") or [])
    total = info.get("playlist_count")
    total = max(len(entries), total if isinstance(total, int) else len(entries))
    unavailable = []
    for index, entry in enumerate(entries, 1):
        entry = entry or {}
        title = entry.get("title") or ""
        availability = entry.get("availability")
        if title and title.casefold() not in ("[deleted video]", "[private video]", "deleted video", "private video") and availability not in ("private", "needs_auth", "premium_only", "subscriber_only"):
            continue
        video_id = entry.get("id") or ""
        reason = ("Video privado." if availability == "private" or "private video" in title.casefold()
                  else "Video eliminado." if "deleted video" in title.casefold()
                  else "Requiere acceso o iniciar sesión." if availability in ("needs_auth", "premium_only", "subscriber_only")
                  else "No disponible en la consulta: YouTube no proporciona el título. No se puede confirmar si está eliminado, privado o restringido.")
        unavailable.append(dict(position=entry.get("playlist_index") or index,
                                title=title or "Título no disponible", reason=reason,
                                url="https://www.youtube.com/watch?v=" + video_id if video_id else ""))
    return dict(title=info.get("title") or "Playlist", total=total, received=len(entries),
                readable=len(entries) - len(unavailable), unavailable=unavailable,
                unaccounted=total - len(entries))


def error_reason(error):
    message = str(error)
    lowered = message.casefold()
    if "429" in lowered or "too many requests" in lowered:
        prefix = "YouTube limitó las consultas. Espera unos minutos y reintenta."
    elif "timed out" in lowered or "timeout" in lowered:
        prefix = "Se agotó el tiempo de espera; comprueba la conexión y reintenta."
    elif "sign in" in lowered or "not a bot" in lowered:
        prefix = "YouTube solicita verificar la sesión; puede ser necesario configurar cookies."
    else:
        prefix = "No se pudo completar la consulta."
    return prefix + " Detalle: " + message


def selection_transfer(records):
    """Audita las elecciones antes de deduplicar los enlaces enviados a la cola."""
    groups = {}
    for record in records:
        url = record.get("url", "").strip()
        if not url:
            raise ValueError(f"La elección de {record.get('query', 'una canción')} no tiene enlace.")
        groups.setdefault(url, []).append(record)
    duplicates = [dict(url=url, records=items) for url, items in groups.items() if len(items) > 1]
    return dict(selected=len(records), unique=len(groups), repeated=len(records) - len(groups),
                urls=list(groups), duplicates=duplicates)


def transfer_text(report):
    lines = ["PASO A LA COLA DE DESCARGAS",
             f"{report['selected']} elecciones → {report['unique']} videos únicos; {report['repeated']} enlaces repetidos.",
             "Un mismo video se descarga una sola vez. Esto no es un error de descarga."]
    for group in report["duplicates"]:
        lines.extend(["", "MISMO VIDEO ELEGIDO PARA:",
                      *[f"  • {record['query']} → {record['title']}" for record in group["records"]],
                      "  Enlace compartido: " + group["url"]])
    return "\n".join(lines)
